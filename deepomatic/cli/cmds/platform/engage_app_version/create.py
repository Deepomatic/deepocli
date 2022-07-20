from ...utils import (
    PlatformCommand,
    valid_path,
)
from ..utils import EngagePlatformManager


class CreateCommand(PlatformCommand):
    """Create a new EngageAppVersion."""

    def setup(self, subparsers):
        parser = super(CreateCommand, self).setup(subparsers)
        parser.add_argument('-w', '--workflow', required=True, type=valid_path, help="Path to the workflow yaml file")
        parser.add_argument('-c', '--custom_nodes', type=valid_path, help="Path to the custom nodes python file")
        parser.add_argument('-i', '--engage_app_id', required=True, type=str, help="EngageApp id for this EngageAppVersion")
        parser.add_argument('-p', '--base_major_version', default=None, type=str, help="Previous major EngageAppVersion version")
        parser.add_argument(
            '-r',
            '--recognition-version-ids',
            required=True,
            nargs="*",
            type=int,
            help="List of Recognition Version Id, one for each Recognition Spec in the EngageAppVersion version", default=[]
        )
        return parser

    def run(self,
            engage_app_id,
            workflow,
            custom_nodes,
            recognition_version_ids,
            base_major_version,
            **kwargs):

        return EngagePlatformManager().create_app_version(
            engage_app_id,
            workflow,
            custom_nodes,
            recognition_version_ids,
            base_major_version
        )
