from ...utils import Command
from ..utils import EngagePlatformManager


class DeleteCommand(Command):
    """
        Delete an Engage App
    """

    def setup(self, subparsers):
        parser = super(DeleteCommand, self).setup(subparsers)
        parser.add_argument('-i', '--id', required=True, type=str, help="Engage App id")
        return parser

    def run(self, id, **kwargs):
        return EngagePlatformManager().delete(id)
