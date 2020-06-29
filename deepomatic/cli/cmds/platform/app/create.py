from ...utils import Command, valid_path
from ..utils import PlatformManager


class CreateCommand(Command):
    """
        Create a new app
    """

    def setup(self, subparsers):
        parser = super(CreateCommand, self).setup(subparsers)
        parser.add_argument('-n', '--name', required=True, type=str, help="App name")
        parser.add_argument('-d', '--description', type=str, help="App description")
        parser.add_argument('-w', '--workflow', required=True, type=valid_path, help="Path to the workflow yaml file")
        parser.add_argument('-c', '--custom_nodes', type=valid_path, help="Path to the custom nodes python file")
        return parser

    def run(self, name, description, workflow, custom_nodes, **kwargs):
        PlatformManager().create_app(name, description, workflow, custom_nodes)
