# -*- coding: utf-8 -*-
import os
import json
import uuid
import logging
from ...thread_base import Greenlet
from ...common import SUPPORTED_IMAGE_INPUT_FORMAT
from ...json_schema import JSONSchemaType, validate_json


BATCH_SIZE = int(os.getenv('DEEPOMATIC_CLI_ADD_IMAGES_BATCH_SIZE', '10'))
LOGGER = logging.getLogger(__name__)


class UploadImageGreenlet(Greenlet):
    def __init__(self, exit_event, input_queue, current_messages,
                 helper, task, on_progress=None, set_metadata_path=False,
                 **kwargs):
        super(UploadImageGreenlet, self).__init__(exit_event, input_queue,
                                                  current_messages=current_messages)
        self.args = kwargs
        self.on_progress = on_progress
        self._helper = helper
        self._task = task
        self._set_metadata_path = set_metadata_path

    def process_msg(self, msg):
        url, batch = msg
        files = {}
        meta = {}
        for file in batch:
            try:
                self.current_messages.report_message()

                # Update file
                files.update({file['key']: open(file['path'], 'rb')})

                # Update corresponding metadata
                file_meta = file.get('meta', {})
                file_metadata = file_meta.get('metadata', '{}')
                if type(file_metadata) is str:
                    file_metadata = json.loads(file_metadata)
                if self._set_metadata_path:
                    file_metadata.update({'image_path': file['path']})
                file_meta['metadata'] = json.dumps(file_metadata)
                meta[file['key']] = file_meta
            except RuntimeError as e:
                self.current_messages.report_error()
                LOGGER.error('Something when wrong with {}: {}. Skipping it.'.format(file['path'], e))
        try:
            rq = self._helper.post(url, data={"objects": json.dumps(meta)}, content_type='multipart/mixed', files=files)
            self._task.retrieve(rq['task_id'])
        except RuntimeError as e:
            self.current_messages.report_errors(len(meta))
            LOGGER.error("Failed to upload batch of images {}: {}.".format(files, e))

        for fd in files.values():
            try:
                fd.close()
            except Exception:
                pass

        if self.on_progress:
            self.on_progress(len(batch))
        self.current_messages.report_successes(len(batch))


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

    def fill_queue(self, files, org_slug, project_name):
        total_files = 0
        url = 'orgs/{}/datasets/{}/images/batch/'.format(org_slug, project_name)
        batch = []

        for upload_file in files:
            extension = os.path.splitext(upload_file)[1].lower()
            # If it's an image file add it to the queue
            if extension in SUPPORTED_IMAGE_INPUT_FORMAT:
                meta = {'file_type': 'image'}
                batch = self.fill_flush_batch(url, batch, upload_file, meta=meta)
                total_files += 1

            # If it's a txt, deal with it accordingly
            elif extension == '.txt':
                with open(upload_file, 'r') as fd:
                    line_number = 0
                    for line in fd:
                        line_number += 1
                        line = json.loads(line)
                        is_valid_json, error, schema_type = validate_json(line)
                        if schema_type == JSONSchemaType.STUDIO_HEADER:
                            self.post_header(org_slug, project_name, line)
                        elif schema_type == JSONSchemaType.STUDIO_INPUT:
                            input = line.pop('data')[0]
                            if 'file' in input:
                                img_loc = input['file']
                                file_path = os.path.join(os.path.dirname(upload_file), img_loc)
                                if not os.path.isfile(file_path):
                                    LOGGER.error("Can't find file named {}".format(img_loc))
                                    continue
                                batch = self.fill_flush_batch(url, batch, file_path, meta=line)
                                total_files += 1
                            else:
                                LOGGER.error("Line {} invalid \"{}\". Skipping it".format(line_number, line))
                        else:
                            LOGGER.error("Line {} invalid \"{}\". Skipping it".format(line_number, line))
            else:
                LOGGER.info("File {} not supported. Skipping it.".format(upload_file))
        self.flush_batch(url, batch)
        return total_files

    def post_files(self, org_slug, project_name, files):
        # Retrieve endpoint
        try:
            request = 'orgs/{}/projects/{}/'.format(org_slug, project_name)
            self._helper.get(request)
        except RuntimeError:
            raise RuntimeError("Can't find the project {}".format(project_name))
        return self.fill_queue(files, org_slug, project_name)

    def post_header(self, org_slug, project_name, project_header):
        request = 'orgs/{}/projects/{}/create_views/'.format(org_slug, project_name)
        self._helper.post(request, data=project_header)
