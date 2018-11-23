import sys
import progressbar
import logging

from deepocli.cli_parser import run

def main(args=None):
    progressbar.streams.wrap_stderr()
    logging.basicConfig(level=logging.INFO)

    """The main routine."""
    if args is None:
        args = sys.argv[1:]
    run(args)

if __name__ == "__main__":
    main()