# -*- coding: utf-8 -*-
import os
import json
import uuid
import logging
from ...thread_base import Greenlet
from ...common import SUPPORTED_IMAGE_INPUT_FORMAT, SUPPORTED_VIDEO_INPUT_FORMAT

BATCH_SIZE = int(os.getenv('DEEPOMATIC_CLI_ADD_IMAGES_BATCH_SIZE', '10'))
LOGGER = logging.getLogger(__name__)


class UploadImageGreenlet(Greenlet):
    def __init__(self, exit_event, input_queue, helper, task, on_progress=None, **kwargs):
        super(UploadImageGreenlet, self).__init__(exit_event, input_queue)
        self.args = kwargs
        self.on_progress = on_progress
        self._helper = helper
        self._task = task

    def process_msg(self, msg):
        url, batch = msg
        files = {}
        meta = {}
        for file in batch:
            try:
                files.update({file['key']: open(file['path'], 'rb')})
                if 'meta' in file:
                    meta.update({file['key']: file['meta']})
            except RuntimeError as e:
                LOGGER.error('Something when wrong with {}: {}. Skipping it.'.format(file['path'], e))
        try:
            rq = self._helper.post(url, data={"objects": json.dumps(meta)}, content_type='multipart/form', files=files)
            self._task.retrieve(rq['task_id'])
        except RuntimeError as e:
            LOGGER.error("Failed to upload batch of images {}: {}.".format(files, e))

        for fd in files.values():
            try:
                fd.close()
            except Exception:
                pass

        if self.on_progress:
            self.on_progress(len(batch))
        self.task_done()


class DatasetFiles(object):
    def __init__(self, helper, output_queue):
        self._helper = helper
        self.output_queue = output_queue

    def flush_batch(self, url, batch):
        if len(batch) > 0:
            self.output_queue.put((url, batch))
        return []

    def fill_flush_batch(self, url, batch, path, meta=None):
        image_key = uuid.uuid4().hex
        img = {"key": image_key, "path": path}
        if meta is not None:
            meta['location'] = image_key
            img['meta'] = meta
        batch.append(img)
        if len(batch) >= BATCH_SIZE:
            return self.flush_batch(url, batch)
        return batch

    def fill_queue(self, files, dataset_name, commit_pk):
        total_files = 0
        url = 'v1-beta/datasets/{}/commits/{}/images/batch/'.format(dataset_name, commit_pk)
        batch = []

        for file in files:
            # If it's an file, add it to the queue
            extension = os.path.splitext(file)[1].lower()
            if extension in SUPPORTED_IMAGE_INPUT_FORMAT:
                meta = {'file_type': 'image'}
                batch = self.fill_flush_batch(url, batch, file, meta=meta)
                total_files += 1
            elif extension in SUPPORTED_VIDEO_INPUT_FORMAT:
                meta = {'file_type': 'video'}
                batch = self.fill_flush_batch(url, batch, file, meta=meta)
                total_files += 1
            # If it's a json, deal with it accordingly
            elif extension == '.json':
                # Verify json validity
                try:
                    with open(file, 'r') as fd:
                        json_objects = json.load(fd)
                except ValueError as e:
                    LOGGER.error("Can't read file {}: {}. Skipping it.".format(file, e))
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
                    obj_extension = json_objects['location'].split('.')[-1]
                    if obj_extension in SUPPORTED_IMAGE_INPUT_FORMAT:
                        json_objects = {'images': [json_objects]}
                    elif obj_extension in SUPPORTED_VIDEO_INPUT_FORMAT:
                        json_objects = {'videos': [json_objects]}

                for ftype in ['images', 'videos']:
                    file_list = json_objects.get(ftype, None)
                    if file_list is not None:
                        for img_json in file_list:
                            img_loc = img_json['location']
                            img_json['file_type'] = ftype[:-1]
                            file_path = os.path.join(os.path.dirname(file), img_loc)
                            if not os.path.isfile(file_path):
                                LOGGER.error("Can't find file named {}".format(img_loc))
                                continue
                            batch = self.fill_flush_batch(url, batch, file_path, meta=img_json)
                            total_files += 1
        self.flush_batch(url, batch)
        return total_files

    def post_files(self, dataset_name, files):
        # Retrieve endpoint
        try:
            ret = self._helper.get('datasets/' + dataset_name + '/')
        except RuntimeError:
            raise RuntimeError("Can't find the dataset {}".format(dataset_name))
        commit_pk = ret['commits'][0]['uuid']
        return self.fill_queue(files, dataset_name, commit_pk)
