from ...utils import PlatformCommand
from ..utils import DrivePlatformManager


class CreateCommand(PlatformCommand):
    """Create a new DriveApp."""

    def setup(self, subparsers):
        parser = super(CreateCommand, self).setup(subparsers)
        parser.add_argument('-n', '--name', required=True, type=str, help="DriveApp name")
        parser.add_argument('-d', '--description', type=str, help="DriveApp description")
        parser.add_argument('-s', '--services', required=True, nargs="*", type=str,
                            help="Services needed by the DriveApp.", default=[])
        return parser

    def run(self, name, description, services, **kwargs):
        return DrivePlatformManager().create_app(name, description, services)
