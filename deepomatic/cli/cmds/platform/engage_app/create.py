from ...utils import Command
from ..utils import EngagePlatformManager


class CreateCommand(Command):
    """Create a new Engage App."""

    def setup(self, subparsers):
        parser = super(CreateCommand, self).setup(subparsers)
        parser.add_argument('-n', '--name', required=True, type=str, help="Engage App name")
        return parser

    def run(self, name, **kwargs):
        return EngagePlatformManager().create_app(name)
