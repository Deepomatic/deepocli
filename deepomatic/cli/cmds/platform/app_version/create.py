from ...utils import Command
from ..utils import PlatformManager


class CreateCommand(Command):
    """
        Create a new app-version
    """

    def setup(self, subparsers):
        parser = super(CreateCommand, self).setup(subparsers)
        parser.add_argument('-n', '--name', required=True, type=str, help="AppVersion name")
        parser.add_argument('-d', '--description', type=str, help="AppVersion description")
        parser.add_argument('-a', '--app_id', required=True, type=str, help="App id for this AppVersion")
        parser.add_argument('-r', '--recognition-version-ids', required=True, nargs="*", type=int,
                            help="List of Recognition Version Id, one for each Recognition Spec in the App", default=[])
        return parser

    def run(self, app_id, name, description, recognition_version_ids, **kwargs):
        return PlatformManager().create_app_version(app_id, name, description, recognition_version_ids)
