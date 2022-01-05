from ...utils import PlatformCommand
from ..utils import EngagePlatformManager


class CreateCommand(PlatformCommand):
    """Create a new EngageApp."""

    def setup(self, subparsers):
        parser = super(CreateCommand, self).setup(subparsers)
        parser.add_argument('-n', '--name', required=True, type=str, help="EngageApp name")
        parser.add_argument(
            '-t',
            '--application_type',
            type=str,
            help="Engage App type (INFERENCE, WORKFLOW, FIELD_SERVICES, VIDEO). Default to FIELD_SERVICES."
        )
        return parser

    def run(self, name, application_type, **kwargs):
        return EngagePlatformManager().create_app(name, application_type)
