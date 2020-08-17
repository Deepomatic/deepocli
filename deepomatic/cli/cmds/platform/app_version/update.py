from ...utils import Command
from ..utils import PlatformManager


class UpdateCommand(Command):
    """
        Update an existing app version
    """

    def setup(self, subparsers):
        parser = super(UpdateCommand, self).setup(subparsers)
        parser.add_argument('-i', '--id', required=True, type=str, help="App version id")
        return parser

    def run(self, id, **kwargs):
        PlatformManager().update_app_version(id)
