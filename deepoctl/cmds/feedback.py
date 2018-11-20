import sys
from .studio_helpers.http_helper import HTTPHelper
from .studio_helpers.image import Image
from .studio_helpers.task import Task

###############################################################################

API_HOST = 'https://studio.deepomatic.com/api/'


###############################################################################

class Client(object):

    def __init__(self, token=None, verify_ssl=True, check_query_parameters=True, host=None, user_agent_suffix='', pool_maxsize=20):
        if host is None:
            host = API_HOST

        self.http_helper = HTTPHelper(token, verify_ssl, host, check_query_parameters, user_agent_suffix, pool_maxsize)
        self.image = Image(self.http_helper)
        self.task = Task(self.http_helper)

def main(args):
    clt = Client()
    for path in args.get('path', []):
        clt.image.post_images(args.get('dataset_name', ''), path, args.get('org_slug', ''), args.get('recursive', False))
    print("Done")
