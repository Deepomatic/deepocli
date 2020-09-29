from ..utils import Command
from ...lib.site import SiteManager


class UpdateCommand(Command):
    """
        Update an existing site
    """

    def setup(self, subparsers):
        parser = super(UpdateCommand, self).setup(subparsers)
        parser.add_argument('-i', '--id', required=True, type=str, help="Site id")
        parser.add_argument('-v', '--app_version_id', required=True, type=str, help="AppVersion id")
        return parser

    def run(self, id, app_version_id, **kwargs):
        return SiteManager().update(id, app_version_id)
