import os
import sys
import logging
import argparse
import argcomplete
from .cmds import AVAILABLE_COMMANDS
from .version import __version__, __title__


class ParserWithHelpOnError(argparse.ArgumentParser):
    """
    Modifies argparser to display the help whenever an error is triggered.
    """

    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(1)


def argparser_init():
    # Initialize main argparser and version command
    argparser = ParserWithHelpOnError(prog='deepo')
    argparser.add_argument(
        '-v', '--version', action='version',
        version='{title} {version}'.format(title=__title__, version=__version__)
    )

    subparsers = argparser.add_subparsers(dest='command', help='')
    subparsers.required = True
    return argparser, subparsers


def run(args):
    # deprecated commands (TODO: migrate to RunCommand() ?)
    argparser, subparsers = argparser_init()

    for command in AVAILABLE_COMMANDS:
        command.setup(subparsers)

    subparsers.required = True
    argcomplete.autocomplete(argparser)

    args = argparser.parse_args(args)

    # Update the log level accordingly
    if args.verbose:
        log_level = logging.DEBUG
        log_format = '[%(levelname)s %(name)s %(asctime)s %(process)d %(thread)d %(filename)s:%(lineno)s] %(message)s'
    else:
        log_level = os.getenv('DEEPOMATIC_LOG_LEVEL', logging.INFO)
        log_format = '[%(levelname)s %(asctime)s] %(message)s'
    logging.basicConfig(level=log_level, format=log_format)

    result = args.func(vars(args))

    if result:
        # FIXME: Probably worth using a dataclass or a wrapper around result
        # We want to have Exception raising when --json-output is used with unsuported command.
        if args.json_output:
            assert isinstance(result, (tuple)), argparse.ArgumentTypeError("--json-output not available for this command.")
            _, data = result
            print(data)
        else:
            if not isinstance(result, (tuple)):
                print(result)
            else:
                messages, data = result
                print("\n".join(messages).format(**data))

    return result
