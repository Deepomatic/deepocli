from ...utils import Command
from ..utils import PlatformManager


class CreateCommand(Command):
    """
        Create a new app-version
    """

    def setup(self, subparsers):
        parser = super(CreateCommand, self).setup(subparsers)
        parser.add_argument('-n', '--name', required=True, type=str, help="")
        parser.add_argument('-a', '--app_id', required=True, type=str, help="")
        parser.add_argument('-r', '--recognition-version-ids', required=True, nargs="*", type=int, help="", default=[])
        return parser

    def run(self, app_id, name, recognition_version_ids, **kwargs):
        PlatformManager().create_app_versions(app_id, name, recognition_version_ids)
