from ...utils import PlatformCommand
from ..utils import DrivePlatformManager


class UpdateCommand(PlatformCommand):
    """Update an existing DriveApp."""

    def setup(self, subparsers):
        parser = super(UpdateCommand, self).setup(subparsers)
        parser.add_argument('-i', '--drive_app_id', required=True, type=str, help="DriveApp id")
        parser.add_argument('-n', '--name', type=str, help="DriveApp name")
        parser.add_argument('-d', '--description', type=str, help="DriveApp description")
        return parser

    def run(self, drive_app_id, name, description, **kwargs):
        return DrivePlatformManager().update_app(drive_app_id, name, description)
