import logging
import pathlib

logger = logging.getLogger(__name__)


class Command(object):
    """
        Base command, use docstring to fill the command help
        The next lines are used for filling the command description
    """

    def __init__(self):
        self.name = self.__class__.__name__.lower().replace("command", "")
        self.help, _, self.description = self.__class__.__doc__.strip().partition('\n')

    def setup(self, subparsers):
        parser = subparsers.add_parser(self.name, help=self.help, description=self.description)
        parser.set_defaults(func=lambda args: self.run(**args))

        subcommands = [command for command in [getattr(self.__class__, attr) for attr in dir(
            self.__class__)] if isinstance(command, type) and issubclass(command, Command)]
        if subcommands:
            subparser = parser.add_subparsers(dest='{} command'.format(self.name), help='')
            subparser.required = True
            for subcommand in subcommands:
                subcommand().setup(subparser)
        # add verbose
        parser.add_argument('--verbose', dest='verbose', action='store_true',
                            help='Increase output verbosity.')

        return parser

    def run(self, *args, **kwargs):
        print(type(self).__name__, args, kwargs)


def valid_path(original_path):
    path = pathlib.Path(original_path)
    if not path.exists():
        raise IOError("'{}' file does not exist".format(original_path))
    return path
