# -*- coding: utf-8 -*-

import os
import sys
import logging
import threading
from tqdm import tqdm
from deepomatic.api.http_helper import HTTPHelper
from deepomatic.cli.cmds.studio_helpers.file import DatasetFiles, UploadImageGreenlet
from deepomatic.cli.cmds.studio_helpers.task import Task
from deepomatic.cli.common import TqdmToLogger, Queue, SUPPORTED_FILE_INPUT_FORMAT
from deepomatic.cli.thread_base import Pool, MainLoop, CurrentMessages
from deepomatic.cli.version import __title__, __version__

###############################################################################

GREENLET_NUMBER = int(os.getenv('DEEPOMATIC_CLI_ADD_IMAGES_CONCURRENCY', 5))
LOGGER = logging.getLogger(__name__)
API_HOST = os.getenv('STUDIO_URL', 'https://studio.deepomatic.com/api/')
DEFAULT_USER_AGENT_PREFIX = user_agent_prefix = '{}/{}'.format(
    __title__, __version__)

###############################################################################


class Client(object):
    def __init__(self, api_key=None, user_agent_prefix=DEFAULT_USER_AGENT_PREFIX, pool_maxsize=GREENLET_NUMBER):
        self.http_helper = HTTPHelper(api_key=api_key, host=API_HOST, user_agent_prefix=user_agent_prefix,
                                      pool_maxsize=pool_maxsize, version=None)
        self.task = Task(self.http_helper)


def get_all_files_with_ext(path, supported_ext, recursive=True):
    """Scans path to find all supported extensions."""
    all_files = []
    if os.path.isfile(path):
        ext_file = os.path.splitext(path)[1].lower()
        if ext_file not in supported_ext:
            LOGGER.warning(
                "The path {} is neither a supported file {} nor a directory, it has been ignored.".format(path, supported_ext))
        else:
            all_files.append(path)
    elif os.path.isdir(path):
        for file in os.listdir(path):
            file_path = os.path.join(path, file)
            if recursive:
                all_files.extend(get_all_files_with_ext(file_path, supported_ext))
            elif os.path.isfile(file_path) and os.path.splitext(file_path)[1].lower() in supported_ext:
                all_files.append(file_path)

    return all_files


def get_all_files(paths, find_txt=False, recursive=True):
    """Retrieves all files from paths, either images or txt if specified."""
    # Make sure path is a list
    paths = [paths] if not isinstance(paths, list) else paths

    # Go through all paths and find corresponding files
    file_ext = ['.txt'] if find_txt else SUPPORTED_FILE_INPUT_FORMAT
    files = []
    for path in paths:
        files += get_all_files_with_ext(path, file_ext, recursive)

    return files


class AddImageManager(object):

    def upload(self, args):
        # Initialize deepomatic client
        clt = Client()

        # Retrieve arguments (must be the same as the parser)
        project_name = args.get('project')
        org_slug = args.get('org')

        paths = args.get('input', [])
        txt_file = args.get('txt_file', False)
        recursive = args.get('recursive', False)
        set_metadata_path = args.get('set_metadata_path', False)

        # Scan to find all files
        files = get_all_files(
            paths=paths, find_txt=txt_file, recursive=recursive)

        # TODO: add a maxsize to avoid taking too much memories
        # This implies reading twice to get the total_files
        queue = Queue()

        dataset_files = DatasetFiles(clt.http_helper, queue)
        total_files = dataset_files.post_files(org_slug, project_name, files)

        exit_event = threading.Event()

        current_messages = CurrentMessages()

        # Initialize progress bar
        tqdmout = TqdmToLogger(LOGGER, level=logging.INFO)
        pbar = tqdm(total=total_files, file=tqdmout,
                    desc='Uploading images', smoothing=0)

        pools = [
            Pool(GREENLET_NUMBER, UploadImageGreenlet,
                 thread_args=(exit_event, queue, current_messages,
                              clt.http_helper, clt.task, pbar.update,
                              set_metadata_path))
        ]

        # Start uploading
        loop = MainLoop(pools, [queue], pbar, exit_event, current_messages)
        try:
            loop.run_forever()
        except Exception:
            loop.cleanup()
            raise

        # If the process encountered an error, the exit code is 1.
        # If the process is interrupted using SIGINT (ctrl + C) or SIGTERM, the threads are stopped, and
        # the exit code is 0.
        if exit_event.is_set():
            sys.exit(1)
