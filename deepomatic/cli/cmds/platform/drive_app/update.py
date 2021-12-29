from ...utils import Command
from ..utils import DrivePlatformManager


class UpdateCommand(Command):
    """Update an existing DriveApp."""

    def setup(self, subparsers):
        parser = super(UpdateCommand, self).setup(subparsers)
        parser.add_argument('-i', '--id', required=True, type=str, help="DriveApp id")
        parser.add_argument('-n', '--name', type=str, help="DriveApp name")
        parser.add_argument('-d', '--description', type=str, help="DriveApp description")
        return parser

    def run(self, id, name, description, **kwargs):
        return DrivePlatformManager().update_app(id, name, description)
