from ..utils import Command
from ...lib.site import SiteManager


class DeleteCommand(Command):
    """
        Delete a Site
    """

    def setup(self, subparsers):
        parser = super(DeleteCommand, self).setup(subparsers)
        parser.add_argument('-i', '--id', required=True, type=str, help="Site id")
        return parser

    def run(self, id, **kwargs):
        return SiteManager().delete(id)
