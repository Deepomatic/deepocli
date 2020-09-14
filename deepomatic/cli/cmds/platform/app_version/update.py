from ...utils import Command
from ..utils import PlatformManager


class UpdateCommand(Command):
    """
        Update an existing app version
    """

    def setup(self, subparsers):
        parser = super(UpdateCommand, self).setup(subparsers)
        parser.add_argument('-i', '--id', required=True, type=str, help="App version id")
        parser.add_argument('-n', '--name', type=str, help="AppVersion name")
        parser.add_argument('-d', '--description', type=str, help="AppVersion description")
        return parser

    def run(self, id, name, description, **kwargs):
        return PlatformManager().update_app_version(id, name, description)
