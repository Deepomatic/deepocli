from ...utils import Command
from ..utils import PlatformManager


class InspectCommand(Command):
    """
        Inspect a workflow
    """

    def setup(self, subparsers):
        parser = super(InspectCommand, self).setup(subparsers)
        parser.add_argument('workflow_path', type=str, help="Path to the directory containing the workflow's files")
        return parser

    def run(self, workflow_path, **kwargs):
        return PlatformManager.inspect(workflow_path)
