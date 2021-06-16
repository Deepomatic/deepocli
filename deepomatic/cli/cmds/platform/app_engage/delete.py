from ...utils import Command
from ..utils import PlatformManager


class DeleteCommand(Command):
    """
        Delete an app engage
    """

    def setup(self, subparsers):
        parser = super(DeleteCommand, self).setup(subparsers)
        parser.add_argument('-i', '--id', required=True, type=str, help="AppEngage id")
        return parser

    def run(self, id, **kwargs):
        return PlatformManager().delete_app_engage(id)
