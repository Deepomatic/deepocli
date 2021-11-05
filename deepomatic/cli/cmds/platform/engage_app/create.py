from ...utils import Command, valid_path
from ..utils import EngagePlatformManager


class CreateCommand(Command):
    """
        Create a new Engage App
    """

    def setup(self, subparsers):
        parser = super(CreateCommand, self).setup(subparsers)
        parser.add_argument('-n', '--name', required=True, type=str, help="Engage App name")
        parser.add_argument('-w', '--workflow', default=None, type=valid_path, help="Path to the workflow yaml file")
        parser.add_argument('-c', '--custom_nodes', type=valid_path, help="Path to the custom nodes python file")
        return parser

    def run(self, name, workflow, custom_nodes, **kwargs):
        return EngagePlatformManager().create(name, workflow, custom_nodes)
