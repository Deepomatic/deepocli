from ..utils import Command
from ...lib.site import SiteManager


class UpdateCommand(Command):
    """
        Update an existing site
    """

    def setup(self, subparsers):
        parser = super(UpdateCommand, self).setup(subparsers)
        parser.add_argument('-i', '--site_id', required=True, type=str, help="Site id")
        parser.add_argument('-v', '--drive_app_version_id', required=True, type=str, help="DriveAppVersion id")
        return parser

    def run(self, site_id, drive_app_version_id, **kwargs):
        return SiteManager().update(site_id, drive_app_version_id)
