from ...utils import (
    PlatformCommand,
    valid_json
)
from ..utils import DrivePlatformManager


class CreateCommand(PlatformCommand):
    """Create a new DriveAppVersion."""

    def setup(self, subparsers):
        parser = super(CreateCommand, self).setup(subparsers)
        parser.add_argument('-n', '--name', required=True, type=str, help="DriveAppVersion name")
        parser.add_argument('-d', '--description', type=str, help="DriveAppVersion description")
        parser.add_argument('-i', '--drive_app_id', required=True, type=str, help="DriveApp id for this DriveAppVersion")
        parser.add_argument('-s', '--app_specs', default=None, required=True,
                            type=valid_json, help="""
                            JSON specs for the app (if workflow not provided).
                            Example:
                            '[{"recognition_spec_id": 123, "queue_name": "spec_123.forward"}]'
                            """)
        parser.add_argument('-r', '--recognition-version-ids', required=True, nargs="*", type=int,
                            help="List of Recognition Version Id, one for each Recognition Spec in the App", default=[])
        return parser

    def run(self, drive_app_id, name, description, app_specs, recognition_version_ids, **kwargs):
        return DrivePlatformManager().create_app_version(
            drive_app_id,
            name,
            description,
            app_specs,
            recognition_version_ids
        )
