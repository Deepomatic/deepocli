from ...utils import JsonOutputCommand
from ..utils import DrivePlatformManager


class DeleteCommand(JsonOutputCommand):
    """Delete a DriveApp."""

    def setup(self, subparsers):
        parser = super(DeleteCommand, self).setup(subparsers)
        parser.add_argument('-i', '--drive_app_id', required=True, type=str, help="DriveApp id")
        return parser

    def run(self, drive_app_id, **kwargs):
        return DrivePlatformManager().delete_app(drive_app_id)
