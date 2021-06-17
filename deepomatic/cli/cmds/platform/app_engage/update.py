from ...utils import Command, valid_path
from ..utils import EngagePlatformManager


class UpdateCommand(Command):
    """
        Update an existing Engage App
    """

    def setup(self, subparsers):
        parser = super(UpdateCommand, self).setup(subparsers)
        parser.add_argument('-i', '--id', required=True, type=str, help="Engage App id")
        parser.add_argument('-w', '--workflow', default=None, type=valid_path, help="Path to the workflow yaml file")
        parser.add_argument('-c', '--custom_nodes', type=valid_path, help="Path to the custom nodes python file")
        return parser

    def run(self, id, workflow, custom_nodes, **kwargs):
        return EngagePlatformManager().update(id, workflow, custom_nodes)
