from ...utils import Command
from ..utils import PlatformManager


class UpdateCommand(Command):
    """
        Update an existing app
    """

    def setup(self, subparsers):
        parser = super(UpdateCommand, self).setup(subparsers)
        parser.add_argument('-i', '--id', required=True, type=str, help="App id")
        parser.add_argument('-n', '--name', type=str, help="App name")
        parser.add_argument('-d', '--description', type=str, help="App description")
        return parser

    def run(self, id, name, description, **kwargs):
        return PlatformManager().update_app(id, name, description)
