# -*- coding: utf-8 -*-
import os
import sys
import json
import logging
import uuid
import threading
import Queue
from .task import Task
import logging
import time
import signal

supported_formats = ['bmp', 'jpeg', 'jpg', 'jpe', 'png']

q = Queue.Queue()
count = 0
run = True
lock = threading.Lock()


def handler(signum, frame):
    global run, q
    run = False
    print("Stopping...")
    while not q.empty():
        q.get()
        q.task_done()


def worker(self):
    global count
    global run
    global q
    while run:
        try:
            url, data, file = q.get(timeout=2)
            with open(file, 'rb') as fd:
                rq = self._helper.post(url, data={"meta": data}, content_type='multipart/form', files={"file": fd})
            self._task.retrieve(rq['task_id'])
            q.task_done()
            lock.acquire()
            count += 1
            lock.release()
            if count % 10 == 0:
                print('{} files uploaded'.format(count))
        except Queue.Empty:
            pass

def get_files(path, recursive=True):
    if os.path.isfile(path):
        if path.split('.')[-1].lower() in supported_formats:
            yield path
    elif os.path.isdir(path):
        if recursive:
            for root, dirs, files in os.walk(path, topdown=False):
                for name in files:
                    if name.split('.')[-1].lower() in supported_formats:
                        yield os.path.join(root, name)
        else:
            for file in os.listdir(path):
                file_path = os.path.join(path, file)
                if os.path.isfile(file_path) and file_path.split('.')[-1].lower() in supported_formats:
                    yield  file_path
    else:
        raise RuntimeError("The path {} is neither a image file nor a directory".format(path))

def get_json(path, recursive=True):
    if os.path.isfile(path):
        if path.split('.')[-1].lower() == 'json':
            yield path
    elif os.path.isdir(path):
        if recursive:
            for root, dirs, files in os.walk(path, topdown=False):
                for name in files:
                    if name.split('.')[-1].lower() == 'json':
                        yield os.path.join(root, name)
        else:
            for file in os.listdir(path):
                file_path = os.path.join(path, file)
                if os.path.isfile(file_path) and file_path.split('.')[-1].lower() == 'json':
                    yield  file_path
    else:
        raise RuntimeError("The path {} is neither a json file nor a directory".format(path))


class Image(object):
    def __init__(self, helper, task=None):
        self._helper = helper
        if not task:
            task = Task(helper)
        self._task = task


    def post_images(self, dataset_name, path, org_slug, recursive=False, json_file=False):
        global run
        try:
            ret = self._helper.get('datasets/' + dataset_name + '/')
        except RuntimeError as err:
            raise RuntimeError("Can't find the dataset {}".format(dataset_name))
        commit_pk = ret['commits'][0]['uuid']

        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(self, ))
            t.daemon = True
            t.start()
            threads.append(t)

        signal.signal(signal.SIGINT, handler)

        if not isinstance(path, list):
            path = [path]
        for elem in path:
            if not json_file:
                for file in get_files(elem, recursive):
                    tmp_name = uuid.uuid4().hex
                    q.put(('v1-beta/datasets/{}/commits/{}/images/'.format(dataset_name, commit_pk), json.dumps({'location': tmp_name}), file))
            else:
                for file in get_json(elem, recursive):
                    try:
                        with open(file, 'rb') as fd:
                            json_objects = json.load(fd)
                    except ValueError as err:
                        logging.debug(err)
                        logging.error("Can't read file {}, skipping...".format(file))
                        continue
                    if isinstance(json_objects, dict):
                        if 'location' not in json_objects:
                            for ext in ('bmp', 'jpeg', 'jpg', 'jpe', 'png'):
                                tmp_path = os.path.join(os.path.dirname(file), os.path.basename(file).replace('json', ext))
                                if os.path.isfile(tmp_path):
                                    json_objects['location'] = tmp_path
                                    json_objects = [json_objects]
                                    break
                            else:
                                logging.error("Can't find an image named {}".format(os.path.basename(file)))
                                continue
                    for i, json_object in enumerate(json_objects):
                        image_path = os.path.join(os.path.dirname(file), json_object['location'])
                        if not os.path.isfile(image_path):
                            logging.error("Can't find an image named {}".format(json_object['location']))
                            continue
                        image_key = uuid.uuid4().hex
                        json_object['location'] = image_key
                        q.put(('v1-beta/datasets/{}/commits/{}/images/'.format(dataset_name, commit_pk), json.dumps(json_object), image_path))
        while not q.empty() and run:
            time.sleep(2)
        run = False
        q.join()
        for t in threads:
            t.join()
        return True
