from ...utils import Command
from ..utils import PlatformManager


class UpdateCommand(Command):
    """
        Update an existing app
    """

    def setup(self, subparsers):
        parser = super(UpdateCommand, self).setup(subparsers)
        parser.add_argument('-a', '--app_id', required=True, type=str, help="")
        return parser

    def run(self, app_id, **kwargs):
        PlatformManager().update_app(app_id)
