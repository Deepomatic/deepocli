import logging
import os
import re

logger = logging.getLogger(__name__)


class Command(object):
    """
        Base command, use docstring to fill the command help
        The next lines are used for filling the command description
    """

    def __init__(self):
        # The name of a command is the Command class name lowercase and - joined in case of camel case
        camel_case_name = self.__class__.__name__.replace("Command", "")
        self.name = re.sub(r'(?<!^)(?=[A-Z])', '-', camel_case_name).lower()
        self.help, _, self.description = self.__class__.__doc__.strip().partition('\n')

    def setup(self, subparsers):
        parser = subparsers.add_parser(self.name, help=self.help, description=self.description)

        subcommands = [command for command in [getattr(self.__class__, attr) for attr in dir(
            self.__class__)] if isinstance(command, type) and issubclass(command, Command)]
        if subcommands:
            subparser = parser.add_subparsers(dest='{} command'.format(self.name), help='')
            subparser.required = True
            for subcommand in subcommands:
                subcommand().setup(subparser)
        else:
            parser.set_defaults(func=lambda args: self.run(**args))

        # add verbose
        parser.add_argument('--verbose', dest='verbose', action='store_true',
                            help='Increase output verbosity.')

        return parser

    def run(self, *args, **kwargs):
        pass


def valid_path(file_path):
    if not os.path.exists(file_path):
        raise IOError("'{}' file does not exist".format(file_path))
    return file_path
