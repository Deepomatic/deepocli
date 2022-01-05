from ...utils import PlatformCommand
from ..utils import DrivePlatformManager


class UpdateCommand(PlatformCommand):
    """Update an existing DriveAppVersion."""

    def setup(self, subparsers):
        parser = super(UpdateCommand, self).setup(subparsers)
        parser.add_argument('-v', '--drive_app_version_id', required=True, type=str, help="DriveAppVersion id")
        parser.add_argument('-n', '--name', type=str, help="DriveAppVersion name")
        parser.add_argument('-d', '--description', type=str, help="DriveAppVersion description")
        return parser

    def run(self, drive_app_version_id, name, description, **kwargs):
        return DrivePlatformManager().update_app_version(drive_app_version_id, name, description)
