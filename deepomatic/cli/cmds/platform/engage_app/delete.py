from ...utils import Command
from ..utils import EngagePlatformManager


class DeleteCommand(Command):
    """Delete an EngageApp."""

    def setup(self, subparsers):
        parser = super(DeleteCommand, self).setup(subparsers)
        parser.add_argument('-i', '--id', required=True, type=str, help="EngageApp id")
        return parser

    def run(self, id, **kwargs):
        return EngagePlatformManager().delete_app(id)
