# -*- coding: utf-8 -*-
import os
import sys
import json
import uuid
import logging
import threading
from tqdm import tqdm
from .task import Task
from ...thread_base import Queue, Empty, Greenlet, Pool


LOGGER = logging.getLogger(__name__)
GREENLET_NUMBER = 10


class UploadImageGreenlet(Greenlet):
    def __init__(self, exit_event, input_queue, helper, task, on_progress=None, **kwargs):
        super(UploadImageGreenlet, self).__init__(exit_event, input_queue)
        self.args = kwargs
        self.on_progress = on_progress
        self._helper = helper
        self._task = task

    def process_msg(self, msg):
        url, data, file = msg

        try:
            with open(file, 'rb') as fd:
                rq = self._helper.post(url, data={"meta": data}, content_type='multipart/form', files={"file": fd})
                self._task.retrieve(rq['task_id'])
        except RuntimeError as e:
            LOGGER.error("URL {} with file {} failed: {}".format(url, file, e))

        if self.on_progress:
            self.on_progress()
        self.task_done()


class DatasetFiles(object):
    def __init__(self, helper, output_queue):
        self._helper = helper
        self.output_queue = output_queue

    def fill_queue(self, files, dataset_name, commit_pk):
        total_files = 0
        for file in files:
            # If it's an file, add it to the queue
            if file.split('.')[-1].lower() != 'json':
                tmp_name = uuid.uuid4().hex
                self.output_queue.put((
                    'v1-beta/datasets/{}/commits/{}/images/'.format(dataset_name, commit_pk),
                    json.dumps({'location': tmp_name}),
                    file
                ))
                total_files += 1
            # If it's a json, deal with it accordingly
            else:
                # Verify json validity
                try:
                    with open(file, 'r') as fd:
                        json_objects = json.load(fd)
                except ValueError as err:
                    LOGGER.error(err)
                    LOGGER.error("Can't read file {}, skipping..".format(file))
                    continue

                # Check which type of JSON it is:
                # 1) a JSON associated with one single file and following the format:
                #       {"location": "img.jpg", stage": "train", "annotated_regions": [..]}
                # 2) a JSON following Studio format:
                #       {"tags": [..], "images": [{"location": "img.jpg", stage": "train", "annotated_regions": [..]}, {..}]}

                # Check that the JSON is a dict
                if not isinstance(json_objects, dict):
                    LOGGER.error("JSON {} is not a dictionnary.".format(os.path.basename(file)))
                    continue

                # If it's a type-1 JSON, transform it into a type-2 JSON
                if 'location' in json_objects:
                    json_objects = {'images': [json_objects]}

                for i, img_json in enumerate(json_objects['images']):
                    img_loc = img_json['location']
                    file_path = os.path.join(os.path.dirname(file), img_loc)
                    if not os.path.isfile(file_path):
                        LOGGER.error("Can't find file named {}".format(img_loc))
                        continue
                    image_key = uuid.uuid4().hex
                    img_json['location'] = image_key
                    self.output_queue.put((
                        'v1-beta/datasets/{}/commits/{}/images/'.format(dataset_name, commit_pk),
                        json.dumps(img_json),
                        file_path
                    ))
                    total_files += 1
        return total_files

    def post_files(self, dataset_name, files):
        # Retrieve endpoint
        try:
            ret = self._helper.get('datasets/' + dataset_name + '/')
        except RuntimeError:
            raise RuntimeError("Can't find the dataset {}".format(dataset_name))
        commit_pk = ret['commits'][0]['uuid']
        # Fill the queue
        return self.fill_queue(files, dataset_name, commit_pk)
