import sys
import logging

from deepomatic.cli.cli_parser import run

def main(args=None):
    logging.basicConfig(level=logging.INFO)

    """The main routine."""
    if args is None:
        args = sys.argv[1:]
    run(args)

if __name__ == "__main__":
    main()