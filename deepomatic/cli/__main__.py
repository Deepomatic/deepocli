from gevent.monkey import patch_all
patch_all(thread=False, time=False)

import sys
import logging

from .cli_parser import run

def main(args=None):
    logging.basicConfig(level=logging.INFO)

    """The main routine."""
    if args is None:
        args = sys.argv[1:]
    run(args)

if __name__ == "__main__":
    main()
