from ...utils import Command, valid_path
from ..utils import EngagePlatformManager


class CloneCommand(Command):
    """Clone an app-version."""

    def setup(self, subparsers):
        parser = super(CloneCommand, self).setup(subparsers)
        parser.add_argument('--version_id', default=None, type=str, help="Engage AppVersion to clone")
        parser.add_argument('-r', '--recognition-version-ids', required=True, nargs="*", type=int,
                            help="List of Recognition Version Id, one for each Recognition Spec in the App", default=[])
        return parser

    def run(self,
            version_id,
            recognition_version_ids,
            **kwargs):

        return EngagePlatformManager().clone_app_version(
            version_id,
            recognition_version_ids
        )
