# -*- coding: utf-8 -*-

import os
import sys
import logging
import requests
import threading
import platform
from tqdm import tqdm
from deepomatic.api.exceptions import (BadStatus, ServerError,
                                       ClientError, DeepomaticException)
from deepomatic.api.http_helper import HTTPHelper, RequestsTimeout
from deepomatic.api.http_retry import HTTPRetry
from deepomatic.api.version import __title__, __version__
from .studio_helpers.file import DatasetFiles, UploadImageGreenlet
from .studio_helpers.task import Task
from ..common import TqdmToLogger, Queue, SUPPORTED_IMAGE_INPUT_FORMAT, SUPPORTED_VIDEO_INPUT_FORMAT, SUPPORTED_FILE_INPUT_FORMAT
from ..thread_base import Pool, MainLoop


###############################################################################

GREENLET_NUMBER = int(os.getenv('DEEPOMATIC_CLI_ADD_IMAGES_CONCURRENCY', 5))
LOGGER = logging.getLogger(__name__)
API_HOST = os.getenv('STUDIO_URL', 'https://studio.deepomatic.com/api/')

###############################################################################

class StudioHTTPHelper(HTTPHelper):
    def __init__(self, app_id=None, api_key=None, verify_ssl=None,
                 host=None, check_query_parameters=True,
                 user_agent_prefix='', pool_maxsize=20,
                 requests_timeout=RequestsTimeout.FAST, **kwargs):
        
        self.http_retry = kwargs.pop('http_retry', HTTPRetry())

        if len(kwargs) > 0:
            raise TypeError("Too many parameters. HTTPRetry does not handle kwargs: {}".format(kwargs))

        self.requests_timeout = requests_timeout

        if host is None:
            host = os.getenv('DEEPOMATIC_API_URL', API_HOST)
        if verify_ssl is None:
            verify = os.getenv('DEEPOMATIC_API_VERIFY_TLS', '1') == '1'
        if app_id is None:
            app_id = os.getenv('DEEPOMATIC_APP_ID')
        if api_key is None:
            api_key = os.getenv('DEEPOMATIC_API_KEY')
        if app_id is None or api_key is None:
            raise DeepomaticException("Please specify 'app_id' and 'api_key' either by passing those values to the client"
                                      " or by defining the DEEPOMATIC_APP_ID and DEEPOMATIC_API_KEY environment variables.")

        if not host.endswith('/'):
            host += '/'

        python_version = "{0}.{1}.{2}".format(sys.version_info.major, sys.version_info.minor, sys.version_info.micro)

        user_agent_params = {
            'package_title': __title__,
            'package_version': __version__,
            'requests_version': requests.__version__,
            'python_version': python_version,
            'platform': platform.platform()
        }

        user_agent_list = []

        if user_agent_prefix:
            user_agent_list.append(user_agent_prefix)

        user_agent_list += [
            '{package_title}-python-client/{package_version}',
            'requests/{requests_version}',
            'python/{python_version} platform/{platform}',
        ]

        self.user_agent = ' '.join(user_agent_list).format(**user_agent_params)

        self.api_key = str(api_key)
        self.app_id = str(app_id)
        self.verify = verify
        self.host = host
        self.resource_prefix = host

        # This is only used in mixins, this should not stay here
        self.check_query_parameters = check_query_parameters

        headers = {
            'User-Agent': self.user_agent,
            'X-APP-ID': self.app_id,
            'X-API-KEY': self.api_key,
        }
        self.session = requests.Session()
        self.session.headers.update(headers)
        # Use pool_maxsize to cache connections for the same host
        adapter = requests.adapters.HTTPAdapter(pool_maxsize=pool_maxsize)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)


class Client(object):
    def __init__(self, token=None, verify_ssl=True, check_query_parameters=True, host=None, user_agent_prefix='', pool_maxsize=GREENLET_NUMBER):
        if host is None:
            host = API_HOST

        self.http_helper = StudioHTTPHelper(api_key=token, verify_ssl=None, host=host, check_query_parameters=check_query_parameters,
                                      user_agent_prefix=user_agent_prefix, pool_maxsize=pool_maxsize)
        self.task = Task(self.http_helper)


def get_all_files_with_ext(path, supported_ext, recursive=True):
    """Scans path to find all supported extensions."""
    all_files = []
    if os.path.isfile(path) and os.path.splitext(path)[1].lower() in supported_ext:
        all_files.append(path)
    elif os.path.isdir(path):
        for file in os.listdir(path):
            file_path = os.path.join(path, file)
            if recursive:
                all_files.extend(get_all_files_with_ext(
                    file_path, supported_ext))
            elif os.path.isfile(file_path) and os.path.splitext(file_path)[1].lower() in supported_ext:
                all_files.append(file_path)
    else:
        raise RuntimeError(
            "The path {} is neither a supported file {} nor a directory".format(path, supported_ext))

    return all_files


def get_all_files(paths, find_json=False, recursive=True):
    """Retrieves all files from paths, either images or json if specified."""
    # Make sure path is a list
    paths = [paths] if not isinstance(paths, list) else paths

    # Go through all paths and find corresponding files
    file_ext = ['.json'] if find_json else SUPPORTED_FILE_INPUT_FORMAT
    files = []

    for path in paths:
        files += get_all_files_with_ext(path, file_ext, recursive)

    return files


def main(args):
    # Initialize deepomatic client
    clt = Client()

    # Retrieve arguments
    dataset_name = args.get('dataset')

    paths = args.get('input', [])
    json_file = args.get('json_file', False)
    recursive = args.get('recursive', False)
    set_metadata_path = args.get('set_metadata_path', False)

    # Scan to find all files
    files = get_all_files(
        paths=paths, find_json=json_file, recursive=recursive)

    # TODO: add a maxsize to avoid taking too much memories
    # This implies reading twice to get the total_files
    queue = Queue()

    dataset_files = DatasetFiles(clt.http_helper, queue)
    total_files = dataset_files.post_files(dataset_name, files)

    exit_event = threading.Event()

    # Initialize progress bar
    tqdmout = TqdmToLogger(LOGGER, level=logging.INFO)
    pbar = tqdm(total=total_files, file=tqdmout,
                desc='Uploading images', smoothing=0)

    pools = [
        Pool(GREENLET_NUMBER, UploadImageGreenlet,
             thread_args=(exit_event, queue, clt.http_helper, clt.task, pbar.update, set_metadata_path))
    ]

    # Start uploading
    loop = MainLoop(pools, [queue], pbar, exit_event)
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
