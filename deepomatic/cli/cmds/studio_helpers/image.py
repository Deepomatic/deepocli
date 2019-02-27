# -*- coding: utf-8 -*-
import os
import sys
import json
import uuid
import time
import signal
import threading
from tqdm import tqdm
from .task import Task
if sys.version_info >= (3,0):
    import queue as Queue
else:
    import Queue

# Define thread parameters
THREAD_NUMBER = 5
BATCH_SIZE = 10
q = Queue.Queue()
count = 0
run = True
lock = threading.Lock()

def handler(signum, frame):
    global run, q, pbar
    run = False
    pbar.close()
    print("Stopping upload...")
    while not q.empty():
        q.get()
        q.task_done()

def worker(self):
    global count, run, q, pbar
    while run:
        try:
            url, batch = q.get(timeout=2)
            files = {}
            meta = {}
            for file in batch:
                try:
                    files.update({file['key']: open(file['path'], 'rb')})
                    if 'meta' in file:
                        meta.update({file['key']: file['meta']})
                except RuntimeError as e:
                    tqdm.write('Something when wrong with {}, skipping this file...'.format(file['path']), file=sys.stderr)
            try:
                with open(file['path'], 'rb') as fd:
                    rq = self._helper.post(url, data={"objects": json.dumps(meta)}, content_type='multipart/form', files=files)
                self._task.retrieve(rq['task_id'])
            except RuntimeError as e:
                tqdm.write('Annotation format for image named {} is incorrect'.format(file), file=sys.stderr)
            pbar.update(len(files))
            q.task_done()
            lock.acquire()
            count += len(files)
            lock.release()
            for fd in files.values():
                fd.close()
        except Queue.Empty:
            pass

class Image(object):
    def __init__(self, helper, task=None):
        self._helper = helper
        if not task:
            task = Task(helper)
        self._task = task


    def post_images(self, dataset_name, files, org_slug, is_json=False):
        global run, pbar
        try:
            ret = self._helper.get('datasets/' + dataset_name + '/')
        except RuntimeError as err:
            raise RuntimeError("Can't find the dataset {}".format(dataset_name))
        commit_pk = ret['commits'][0]['uuid']
        url = 'v1-beta/datasets/{}/commits/{}/images/batch/'.format(dataset_name, commit_pk)
        # Build the queue
        total_images = 0
        tmp = []
        for file in files:
            # If it's an image, add it to the queue
            if file.split('.')[-1].lower() != 'json':
                image_key = uuid.uuid4().hex
                tmp.append({"key": image_key, "path": file})
                if len(tmp) >= BATCH_SIZE:
                    q.put((url, tmp))
                    total_images += len(tmp)
                    tmp = []
            # If it's a json, deal with it accordingly
            else:
                # Verify json validity
                try:
                    with open(file, 'r') as fd:
                        json_objects = json.load(fd)
                except ValueError as err:
                    tqdm.write(err, file=sys.stderr)
                    tqdm.write("Can't read file {}, skipping...".format(file), file=sys.stderr)
                    continue

                # Check which type of JSON it is:
                # 1) a JSON associated with one single image and following the format:
                #       {"location": "img.jpg", stage": "train", "annotated_regions": [...]}
                # 2) a JSON following Studio format:
                #       {"tags": [...], "images": [{"location": "img.jpg", stage": "train", "annotated_regions": [...]}, {...}]}

                # Check that the JSON is a dict
                if not isinstance(json_objects, dict):
                    tqdm.write("JSON {} is not a dictionnary.".format(os.path.basename(file)), file=sys.stderr)
                    continue

                # If it's a type-1 JSON, transform it into a type-2 JSON
                if 'location' in json_objects:
                    json_objects = {'images': [json_objects]}

                for i, img_json in enumerate(json_objects['images']):
                    img_loc = img_json['location']
                    image_path = os.path.join(os.path.dirname(file), img_loc)
                    if not os.path.isfile(image_path):
                        tqdm.write("Can't find an image named {}".format(img_loc), file=sys.stderr)
                        continue
                    image_key = uuid.uuid4().hex
                    img_json['location'] = image_key
                    tmp.append({"meta": img_json, "key": image_key, "path": image_path})
                    if len(tmp) >= BATCH_SIZE:
                        q.put((url, tmp))
                        total_images += len(tmp)
                        tmp = []
        if len(tmp):
            q.put((url, tmp))
            total_images += len(tmp)


        # Initialize progressbar before starting workers
        print("Uploading images...")
        pbar = tqdm(total=total_images)

        # Initialize threads
        run = True  # reset the value to True in case the program is run multiple times
        threads = []
        for i in range(THREAD_NUMBER):
            t = threading.Thread(target=worker, args=(self, ))
            t.daemon = True
            t.start()
            threads.append(t)
        signal.signal(signal.SIGINT, handler)

        # Process all files
        while not q.empty() and run:
            time.sleep(2)
        run = False

        # Close properly
        q.join()
        for t in threads:
            t.join()
        pbar.close()
        if count == total_images:
            print("All {} images have been uploaded.".format(count))
        else:
            print("{} images out of {} have been uploaded.".format(count, total_images))

        return True
