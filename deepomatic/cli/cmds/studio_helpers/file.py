# -*- coding: utf-8 -*-
import os
import sys
import json
import uuid
import time
import signal
import logging
import threading
from tqdm import tqdm
from .task import Task
from ...common import TqdmToLogger
from ... import thread_base
try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty


THREAD_NUMBER = 5


class UploadImageThread(thread_base.ThreadBase):
    def __init__(self, exit_event, input_queue, helper, task, on_progress=None, **kwargs):
        super(UploadImageThread, self).__init__(exit_event, 'UploadImageThread', input_queue)
        self.args = kwargs
        self.on_progress = on_progress
        self._helper = helper
        self._task = task

    def loop_impl(self):
        try:
            url, data, file = self.input_queue.get(timeout=thread_base.POP_TIMEOUT)
        except Empty:
            return

        try:
            with open(file, 'rb') as fd:
                rq = self._helper.post(url, data={"meta": data}, content_type='multipart/form', files={"file": fd})
                self._task.retrieve(rq['task_id'])
        except RuntimeError as e:
            logging.error("URL {} with file {} failed: {}".format(url, file, e))

        self.input_queue.task_done()
        if self.on_progress:
            self.on_progress()


class File(object):
    def __init__(self, helper, task=None):
        self._helper = helper
        if not task:
            task = Task(helper)
        self._task = task
        self.input_queue = Queue()
        self.total_files = 0


    def fill_queue(self, files, dataset_name, commit_pk):
        for file in files:
            # If it's an file, add it to the queue
            if file.split('.')[-1].lower() != 'json':
                tmp_name = uuid.uuid4().hex
                self.input_queue.put((
                    'v1-beta/datasets/{}/commits/{}/images/'.format(dataset_name, commit_pk),
                    json.dumps({'location': tmp_name}),
                    file
                ))
                self.total_files += 1
            # If it's a json, deal with it accordingly
            else:
                # Verify json validity
                try:
                    with open(file, 'r') as fd:
                        json_objects = json.load(fd)
                except ValueError as err:
                    logging.error(err)
                    logging.error("Can't read file {}, skipping..".format(file))
                    continue

                # Check which type of JSON it is:
                # 1) a JSON associated with one single file and following the format:
                #       {"location": "img.jpg", stage": "train", "annotated_regions": [..]}
                # 2) a JSON following Studio format:
                #       {"tags": [..], "images": [{"location": "img.jpg", stage": "train", "annotated_regions": [..]}, {..}]}

                # Check that the JSON is a dict
                if not isinstance(json_objects, dict):
                    logging.error("JSON {} is not a dictionnary.".format(os.path.basename(file)))
                    continue

                # If it's a type-1 JSON, transform it into a type-2 JSON
                if 'location' in json_objects:
                    json_objects = {'images': [json_objects]}

                for i, img_json in enumerate(json_objects['images']):
                    img_loc = img_json['location']
                    file_path = os.path.join(os.path.dirname(file), img_loc)
                    if not os.path.isfile(file_path):
                        logging.error("Can't find file named {}".format(img_loc))
                        continue
                    image_key = uuid.uuid4().hex
                    img_json['location'] = image_key
                    self.input_queue.put((
                        'v1-beta/datasets/{}/commits/{}/images/'.format(dataset_name, commit_pk),
                        json.dumps(img_json),
                        file_path
                    ))
                    self.total_files += 1


    def post_files(self, dataset_name, files, org_slug, is_json=False):
        # Retrieve endpoint
        try:
            ret = self._helper.get('datasets/' + dataset_name + '/')
        except RuntimeError as err:
            raise RuntimeError("Can't find the dataset {}".format(dataset_name))
        commit_pk = ret['commits'][0]['uuid']

        # Fill the queue
        self.fill_queue(files, dataset_name, commit_pk)

        # Initialize progress bar
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger()
        tqdmout = TqdmToLogger(logger, level=logging.INFO)
        pbar = tqdm(total=self.total_files, file=tqdmout, desc='Uploading images', smoothing=0)

        # Define threads
        exit_event = threading.Event()
        threads = []
        for i in range(THREAD_NUMBER):
            t = UploadImageThread(
                exit_event,
                self.input_queue,
                self._helper,
                self._task,
                on_progress=lambda: pbar.update(1)
            )
            threads.append(t)
        stop_asked = 0

        # Start threads
        for t in threads:
            t.start()

        while True:
            try:
                for t in threads:
                    t.stop_when_no_input()
                break
            except (KeyboardInterrupt, SystemExit):
                stop_asked += 1
                for t in threads:
                    t.stop()
                logging.info("Stopping upload...")
                break

        # Close threads
        for t in threads:
            t.join()
        pbar.close()

        # If the process encountered an error, the exit code is 1.
        # If the process is interrupted using SIGINT (ctrl + C) or SIGTERM, the threads are stopped, and
        # the exit code is 0.
        if exit_event.is_set():
            sys.exit(1)

        return True
