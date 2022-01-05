from ...utils import PlatformCommand
from ..utils import EngagePlatformManager


class DeleteCommand(PlatformCommand):
    """Delete an EngageApp."""

    def setup(self, subparsers):
        parser = super(DeleteCommand, self).setup(subparsers)
        parser.add_argument('-i', '--engage_app_id', required=True, type=str, help="EngageApp id")
        return parser

    def run(self, engage_app_id, **kwargs):
        return EngagePlatformManager().delete_app(engage_app_id)
