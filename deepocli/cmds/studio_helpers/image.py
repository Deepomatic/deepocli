# -*- coding: utf-8 -*-
import os
import sys
import json
import logging
import uuid
from .task import Task

supported_formats = ['bmp', 'jpeg', 'jpg', 'jpe', 'png']
FLUSH_SIZE = 25 # arbitrary size

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
        try:
            ret = self._helper.get('datasets/' + dataset_name + '/')
        except RuntimeError as err:
            raise RuntimeError("Can't find the dataset {}".format(dataset_name))
        commit_pk = ret['commits'][0]['uuid']

        if not isinstance(path, list):
            path = [path]
        rq = []
        files = {}
        for elem in path:
            if not json_file:
                for file in get_files(elem, recursive):
                    tmp_name = uuid.uuid4().hex
                    rq.append({'location': tmp_name})
                    files[tmp_name] = open(file, 'rb')
                    if len(files) > FLUSH_SIZE:
                        self._task.retrieve(self._helper.post('v1/datasets/{}/commits/{}/images/batch/'.format(dataset_name, commit_pk), data=rq, content_type='multipart/form', files=files)['task_id'])
                        rq = []
                        files = {}
            else:
                for file in get_json(elem, recursive):
                    try:
                        with open(file, 'rb') as fd:
                            json_objects = json.load(fd)
                    except ValueError:
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
                        files[image_key] = open(image_path, 'rb')
                        json_object['location'] = image_key
                        rq.append(json_object)
                        if len(files) > FLUSH_SIZE:
                            self._task.retrieve(self._helper.post('v1/datasets/{}/commits/{}/images/batch/'.format(dataset_name, commit_pk), data={"objects": json.dumps(rq)}, content_type='multipart/form', files=files)['task_id'])
                            rq = []
                            files = {}

        # flush
        if len(files):
            self._task.retrieve(self._helper.post('v1/datasets/{}/commits/{}/images/batch/'.format(dataset_name, commit_pk), data={"objects": json.dumps(rq)}, content_type='multipart/form', files=files)['task_id'])
        return True
