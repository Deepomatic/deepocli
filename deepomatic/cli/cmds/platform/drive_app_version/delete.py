from ...utils import PlatformCommand
from ..utils import DrivePlatformManager


class DeleteCommand(PlatformCommand):
    """Delete a DriveAppVersion."""

    def setup(self, subparsers):
        parser = super(DeleteCommand, self).setup(subparsers)
        parser.add_argument('-v', '--drive_app_version_id', required=True, type=str, help="DriveAppVersion id")
        return parser

    def run(self, drive_app_version_id, **kwargs):
        return DrivePlatformManager().delete_app_version(drive_app_version_id)
