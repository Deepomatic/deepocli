import sys
from .cli_parser import run


def main(args=None):
    """The main routine."""
    if args is None:
        args = sys.argv[1:]
    run(args)

if __name__ == "__main__":
    main()
