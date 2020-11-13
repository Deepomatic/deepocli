from deepomatic.api.http_helper import HTTPHelper
from ..version import __title__, __version__


###############################################################################

DEFAULT_USER_AGENT_PREFIX = user_agent_prefix = '{}/{}'.format(
    __title__, __version__)

CLIENTS = {}

###############################################################################


class Client(HTTPHelper):
    def __init__(self, **kwargs):
        super(Client, self).__init__(user_agent_prefix=DEFAULT_USER_AGENT_PREFIX,
                                     version=None, **kwargs)

    def _setup_credentials(self):
        # No credentials
        pass

    def default_headers(self):
        return {
            'User-Agent': self.user_agent,
        }


class CameraCtrl(object):
    def __init__(self, client):
        self.client = client

    def add(self, name, address, fps=None, tcp=True):
        payload = {
            "name": name,
            "address": address,
            "rtsp_transport_protocol": "tcp" if tcp else "udp"
        }
        if fps is not None:
            payload['framerate'] = fps
        return self.client.post('cameras', json=payload)

    def get(self, name):
        return self.client.get('cameras/{}'.format(name))

    def delete(self, name):
        return self.client.delete('cameras/{}'.format(name))

    def start(self, name):
        return self.client.post('cameras/{}/start'.format(name))

    def stop(self, name):
        return self.client.post('cameras/{}/stop'.format(name))

    def list(self):
        return self.client.get('cameras')['results']


def get_client(camera_server_address):
    global CLIENTS
    if camera_server_address not in CLIENTS:
        CLIENTS[camera_server_address] = Client(host=camera_server_address)
    return CLIENTS[camera_server_address]


def get_camera_ctrl(camera_server_address):
    return CameraCtrl(get_client(camera_server_address))
