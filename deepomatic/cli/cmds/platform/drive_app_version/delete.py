from ...utils import Command
from ..utils import DrivePlatformManager


class DeleteCommand(Command):
    """Delete a DriveAppVersion."""

    def setup(self, subparsers):
        parser = super(DeleteCommand, self).setup(subparsers)
        parser.add_argument('-i', '--id', required=True, type=str, help="DriveAppVersion id")
        return parser

    def run(self, id, **kwargs):
        return DrivePlatformManager().delete_app_version(id)
