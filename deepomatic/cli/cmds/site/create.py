from ..utils import Command
from .utils import SiteManager


class CreateCommand(Command):
    """
        create a new site with the specified app
    """

    def setup(self, subparsers):
        parser = super(CreateCommand, self).setup(subparsers)
        parser.add_argument('name', type=str, help="site name")
        parser.add_argument('--app-id', required=True, type=str, help="app id")
        parser.add_argument('--description', required=False, type=str, help="", default="")
        return parser

    def run(self, name, app_id, description, **kwargs):
        site = SiteManager().create(name, app_id, description)
        print(site)