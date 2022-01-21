from ..utils import Command
from ...lib.site import SiteManager


class CreateCommand(Command):
    """Create a new site."""

    def setup(self, subparsers):
        parser = super(CreateCommand, self).setup(subparsers)
        parser.add_argument('-n', '--name', required=True, type=str, help="Site name")
        parser.add_argument('-d', '--description', type=str, help="Site description")
        parser.add_argument('-v', '--drive_app_version_id', required=True, type=str, help="DriveAppVersion id")
        return parser

    def run(self, name, description, drive_app_version_id, **kwargs):
        return SiteManager().create(name, description, drive_app_version_id)
