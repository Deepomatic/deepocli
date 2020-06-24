from ...utils import Command
from ..utils import PlatformManager


class UpdateCommand(Command):
    """
        Update an existing site
    """

    def setup(self, subparsers):
        parser = super(UpdateCommand, self).setup(subparsers)
        parser.add_argument('-s', '--site_id', required=True, type=str, help="site id")
        parser.add_argument('-v', '--app_version_id', required=True, type=str, help="app_version_id")
        return parser

    def run(self, site_id, app_version_id, **kwargs):
        PlatformManager().update_site(site_id, app_version_id)
