from ...utils import Command
from ..utils import PlatformManager


class UpdateCommand(Command):
    """
        Update an existing app version
    """

    def setup(self, subparsers):
        parser = super(UpdateCommand, self).setup(subparsers)
        parser.add_argument('-v', '--app_version_id', required=True, type=str, help="")
        return parser

    def run(self, app_version_id, **kwargs):
        PlatformManager().update_app_versions(app_version_id)
