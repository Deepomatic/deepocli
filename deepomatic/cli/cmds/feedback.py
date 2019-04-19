# -*- coding: utf-8 -*-

import os
import sys
import logging
import threading
from tqdm import tqdm
from .studio_helpers.http_helper import HTTPHelper
from .studio_helpers.file import DatasetFiles, UploadImageGreenlet
from .studio_helpers.task import Task
from ..common import TqdmToLogger, Queue
from ..thread_base import Pool, MainLoop


###############################################################################

GREENLET_NUMBER = 10
LOGGER = logging.getLogger(__name__)
API_HOST = os.getenv('STUDIO_URL', 'https://studio.deepomatic.com/api/')
SUPPORTED_IMG_FORMAT = ['bmp', 'jpeg', 'jpg', 'jpe', 'png']

###############################################################################


class Client(object):
    def __init__(self, token=None, verify_ssl=True, check_query_parameters=True, host=None, user_agent_suffix='', pool_maxsize=GREENLET_NUMBER):
        if host is None:
            host = API_HOST

        self.http_helper = HTTPHelper(token, verify_ssl, host, check_query_parameters, user_agent_suffix, pool_maxsize)
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
    # TODO: detect vulcain json format and convert
    # Initialize deepomatic client
    clt = Client()

    # Retrieve arguments
    dataset_name = args.get('dataset')

    paths = args.get('path', [])
    json_file = args.get('json_file', False)
    recursive = args.get('recursive', False)

    # Scan to find all files
    files = get_all_files(paths=paths, find_json=json_file, recursive=recursive)

    # TODO: add a maxsize to avoid taking too much memories
    # This implies reading twice to get the total_files
    queue = Queue()

    dataset_files = DatasetFiles(clt.http_helper, queue)

    total_files = dataset_files.post_files(dataset_name, files)

    exit_event = threading.Event()

    # # Initialize progress bar
    tqdmout = TqdmToLogger(LOGGER, level=logging.INFO)
    pbar = tqdm(total=total_files, file=tqdmout, desc='Uploading images', smoothing=0)

    pools = [
        Pool(GREENLET_NUMBER, UploadImageGreenlet,
             thread_args=(exit_event, queue, clt.http_helper, clt.task, pbar.update))
    ]

    # Start uploading
    loop = MainLoop(pools, [queue], pbar)
    loop.run_forever()

    # If the process encountered an error, the exit code is 1.
    # If the process is interrupted using SIGINT (ctrl + C) or SIGTERM, the threads are stopped, and
    # the exit code is 0.
    if exit_event.is_set():
        sys.exit(1)
