from ...utils import (
    PlatformCommand,
    valid_path
)
from ..utils import EngagePlatformManager


class CreateFromCommand(PlatformCommand):
    """Create an EngageAppVersion from an other one."""

    def setup(self, subparsers):
        parser = super(CreateFromCommand, self).setup(subparsers)
        parser.add_argument('--from', dest="origin", required=True, type=str, help="EngageAppVersion id used as base")
        parser.add_argument('-w', '--workflow', default=None, type=valid_path, help="Path to the workflow yaml file")
        parser.add_argument('-c', '--custom_nodes', default=None, type=valid_path, help="Path to the custom nodes python file")
        parser.add_argument('-p', '--base_major_version', default=None, type=str, help="Previous major EngageAppVersion version")
        parser.add_argument('-r', '--recognition-version-ids', nargs="*", type=int,
                            help="List of Recognition Version Id, one for each Recognition Spec in the App", default=[])
        return parser

    def run(self,
            origin,
            base_major_version,
            workflow,
            custom_nodes,
            recognition_version_ids,
            **kwargs):

        return EngagePlatformManager().create_app_version_from(
            origin,
            base_major_version,
            workflow,
            custom_nodes,
            recognition_version_ids
        )
