# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
from .studio_helpers.http_helper import HTTPHelper
from .studio_helpers.image import Image
from .studio_helpers.task import Task

###############################################################################

API_HOST = os.getenv('STUDIO_URL', 'https://studio.deepomatic.com/api/')
SUPPORTED_IMG_FORMAT = ['bmp', 'jpeg', 'jpg', 'jpe', 'png']

###############################################################################

class Client(object):
    def __init__(self, token=None, verify_ssl=True, check_query_parameters=True, host=None, user_agent_suffix='', pool_maxsize=20):
        if host is None:
            host = API_HOST

        self.http_helper = HTTPHelper(token, verify_ssl, host, check_query_parameters, user_agent_suffix, pool_maxsize)
        self.image = Image(self.http_helper)
        self.task = Task(self.http_helper)


def get_all_files_with_ext(path, supported_ext, recursive=True):
    """Scans path to find all supported extensions."""
    all_files = []
    if os.path.isfile(path):
        if os.path.splitext(path)[1][1:].lower() in supported_ext:
            all_files.append(path)
    elif os.path.isdir(path):
        for file in os.listdir(path):
            file_path = os.path.join(path, file)
            if recursive:
                all_files.extend(get_all_files_with_ext(file_path, supported_ext))
            else:
                if os.path.isfile(file_path) and os.path.splitext(file_path)[1][1:].lower() in supported_ext:
                    all_files.append(file_path)
    else:
        raise RuntimeError("The path {} is neither a supported file {} nor a directory".format(path, supported_ext))

    return all_files

def get_all_files(paths, find_json=False, recursive=True):
    """Retrieves all files from paths, either images or json if specified."""
    # Make sure path is a list
    paths = [paths] if not isinstance(paths, list) else paths

    # Go through all paths and find corresponding files
    file_ext = ['json'] if find_json else SUPPORTED_IMG_FORMAT
    files = []
    for path in paths:
        files += get_all_files_with_ext(path, file_ext, recursive)

    return files

def main(args):
    # Initialize deepomatic client
    clt = Client()

    # Retrieve arguments
    dataset_name = args.get('dataset')
    org_slug = args.get('organization')
    paths = args.get('path', [])
    json_file = args.get('json_file', False)
    recursive = args.get('recursive', False)

    # Scan to find all files
    files = get_all_files(paths=paths, find_json=json_file, recursive=recursive)

    # Start uploading
    clt.image.post_images(files=files, dataset_name=dataset_name, org_slug=org_slug, is_json=json_file)
