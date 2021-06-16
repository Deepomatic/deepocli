from ...utils import Command, valid_path
from ..utils import PlatformManager


class CreateCommand(Command):
    """
        Create a new app engage
    """

    def setup(self, subparsers):
        parser = super(CreateCommand, self).setup(subparsers)
        parser.add_argument('-n', '--name', required=True, type=str, help="App name")
        parser.add_argument('-w', '--workflow', default=None, type=valid_path, help="Path to the workflow yaml file")
        parser.add_argument('-c', '--custom_nodes', type=valid_path, help="Path to the custom nodes python file")
        return parser

    def run(self, name, workflow, custom_nodes, **kwargs):
        return PlatformManager().create_app_engage(name, workflow, custom_nodes)
