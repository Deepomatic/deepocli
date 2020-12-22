import os
import logging
from contextlib import contextmanager
from deepomatic.api.http_helper import HTTPHelper
from ..version import __title__, __version__


###############################################################################


LOGGER = logging.getLogger(__name__)

DEFAULT_USER_AGENT_PREFIX = '{}/{}'.format(__title__, __version__)

CLIENT = None

###############################################################################


class Client(HTTPHelper):
    def __init__(self, **kwargs):
        super(Client, self).__init__(user_agent_prefix=DEFAULT_USER_AGENT_PREFIX,
                                     version=None, **kwargs)

    def _setup_host(self, host, verify_ssl):
        if host is None:
            host = os.environ['CAMERA_SERVER_URL']
        if verify_ssl is None:
            verify_ssl = os.getenv('CAMERA_SERVER_VERIFY_TLS', '1') == '1'

        if not host.endswith('/'):
            host += '/'

        self.verify_ssl = verify_ssl
        self.host = host

    def _setup_credentials(self, app_id, api_key):
        # No credentials
        pass

    def default_headers(self):
        return {
            'User-Agent': self.user_agent,
        }


class CameraCtrl(object):
    def __init__(self, client):
        self.client = client

    def add(self, name, address):
        return self.client.post('/cameras', json={
            "name": name,
            "address": address,
        })

    def delete(self, name):
        return self.client.delete('/cameras/{}'.format(name))

    def start(self, name):
        return self.client.post('/cameras/{}/start'.format(name))

    def stop(self, name):
        return self.client.post('/cameras/{}/stop'.format(name))

    def list(self):
        return self.client.get('/cameras')


def get_client():
    global CLIENT
    if CLIENT is None:
        CLIENT = Client()
    return CLIENT


def get_camera_ctrl():
    return CameraCtrl(get_client())


@contextmanager
def start_stop_camera(name):
    LOGGER.info("Starting camera '{}'".format(name))
    get_camera_ctrl().start(name)
    try:
        yield
    except Exception:
        LOGGER.info("Stopping camera '{}'".format(name))
        get_camera_ctrl().stop(name)
        raise


@contextmanager
def temp_camera(name, address):
    LOGGER.info("Adding camera '{}'".format(name))
    camera = get_camera_ctrl().add(name, address)
    name = camera['name']

    try:
        with start_stop_camera(name):
            yield camera
    except Exception:
        LOGGER.info("Deleting camera '{}'".format(name))
        get_camera_ctrl().delete(name)
        raise


def add_start_camera(name, address):
    LOGGER.info("Adding camera '{}'".format(name))
    get_camera_ctrl().add(name, address)
    LOGGER.info("Starting camera '{}'".format(name))
    get_camera_ctrl().start(name)


def add(args):
    get_camera_ctrl().add(args.camera_name, args.camera_address)
    LOGGER.info("Camera '{}' added".format(args.camera_name))


def start(args):
    get_camera_ctrl().start(args.camera_name)
    LOGGER.info("Camera '{}' started".format(args.camera_name))


def stop(args):
    get_camera_ctrl().stop(args.camera_name)
    LOGGER.info("Camera '{}' stopped".format(args.camera_name))


def delete(args):
    get_camera_ctrl().delete(args.camera_name)
    LOGGER.info("Camera '{}' delete".format(args.camera_name))


def list(args):
    cameras = get_camera_ctrl().list(args.camera_name)
    LOGGER.info("Cameras: \n{}".format(cameras))


def stream(args):
    add_start_camera(args.camera_name, args.camera_address)
