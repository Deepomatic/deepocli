# -*- coding: utf-8 -*-
import os
import sys
from .task import Task

supported_image_formats = ['bmp', 'jpeg', 'jpg', 'jpe', 'png']

def get_files(path, recursive=True):
    if os.path.isfile(path):
        if path.split('.')[-1].lower() in supported_image_formats:
            yield path
    elif os.path.isdir(path) and recursive:
        if recursive:
            for root, dirs, files in os.walk(path, topdown=False):
                for name in files:
                    if name.split('.')[-1].lower() in supported_image_formats:
                        yield os.path.join(root, name)
        else:
            for file in os.listdir(path):
                file_path = os.path.join(path, file)
                if os.path.isfile(file_path) and file_path.split('.')[-1].lower() in supported_image_formats:
                    yield  file_path
    else:
        raise RuntimeError("The path {} is neither a file nor a directory".format(path))

class Image(object):
    def __init__(self, helper, task=None):
        self._helper = helper
        if not task:
            task = Task(helper)
        self._task = task


    def post_images(self, dataset_name, path, org_slug, recursive=False):
        for dataset in self._helper.get('datasets/')['results']:
            if dataset['name'].lower() == dataset_name.lower():  # name is unique, realname is not
                commit_pk = dataset['commits'][0]['uuid']
                break
        else:
            raise RuntimeError("Can't find the dataset {}".format(dataset_name))

        data = {
            "task": "import_images",
            "org_slug": org_slug,
            "cuuid": commit_pk,
            "dataset_name": dataset_name
        }
        if not isinstance(path, list):
            path = [path]
        files = []
        for elem in path:
            for file in get_files(elem, recursive):
                files.append(('files', open(file, 'rb')))
                if len(files) > 25:  # arbitrary size
                    self._task.retrieve(self._helper.post('action/', data=data, content_type='multipart/form', files=files)['task_id'])
                    files = []
        if len(files):
            self._task.retrieve(self._helper.post('action/', data=data, content_type='multipart/form', files=files)['task_id'])
        return True
