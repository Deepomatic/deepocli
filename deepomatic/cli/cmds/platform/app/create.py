from ...utils import Command, valid_json
from ..utils import PlatformManager


class CreateCommand(Command):
    """
        Create a new app
    """

    def setup(self, subparsers):
        parser = super(CreateCommand, self).setup(subparsers)
        parser.add_argument('-n', '--name', required=True, type=str, help="App name")
        parser.add_argument('-d', '--description', type=str, help="App description")
        parser.add_argument('-s', '--app_specs', default=None,
                            type=valid_json, help="""
                            JSON specs for the app (if workflow not provided).
                            Example:
                            '[{"recognition_spec_id": 123, "queue_name": "spec_123.forward"}]'
                            """)
        return parser

    def run(self, name, description, app_specs, **kwargs):
        return PlatformManager().create_app(name, description, app_specs)
