from ...utils import Command
from ..utils import PlatformManager


class CreateCommand(Command):
    """
        Create a new site
    """

    def setup(self, subparsers):
        parser = super(CreateCommand, self).setup(subparsers)
        parser.add_argument('-n', '--name', required=True, type=str, help="site name")
        parser.add_argument('-v', '--app_version_id', required=True, type=str, help="app version id")
        return parser

    def run(self, name, app_version_id, **kwargs):
        PlatformManager().create_site(name, app_version_id)
