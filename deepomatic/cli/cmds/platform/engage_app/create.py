from ...utils import Command
from ..utils import EngagePlatformManager


class CreateCommand(Command):
    """Create a new Engage App."""

    def setup(self, subparsers):
        parser = super(CreateCommand, self).setup(subparsers)
        parser.add_argument('-n', '--name', required=True, type=str, help="Engage App name")
        parser.add_argument(
            '-t',
            '--application_type',
            type=str,
            help="Engage App type (INFERENCE, WORKFLOW, FIELD_SERVICES, VIDEO). Default to FIELD_SERVICES."
        )
        return parser

    def run(self, name, application_type, **kwargs):
        return EngagePlatformManager().create_app(name, application_type)
