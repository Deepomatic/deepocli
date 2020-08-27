from ...utils import Command
from ..utils import PlatformManager


class DeleteCommand(Command):
    """
        Delete a Site
    """

    def setup(self, subparsers):
        parser = super(DeleteCommand, self).setup(subparsers)
        parser.add_argument('-i', '--id', required=True, type=str, help="Site id")
        return parser

    def run(self, id, **kwargs):
        PlatformManager().delete_site(id)
