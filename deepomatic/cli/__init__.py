from gevent.monkey import patch_all
patch_all(thread=False, time=False)
from .version import __version__
import logging
import os


logging.basicConfig(level=os.getenv('DEEPOMATIC_LOG_LEVEL', 'INFO'),
                    format='[%(levelname)s] %(message)s')
