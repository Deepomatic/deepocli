from ...utils import Command
from ..utils import PlatformManager


class PublishCommand(Command):
    """
        Publish workflow
    """

    def setup(self, subparsers):
        parser = super(PublishCommand, self).setup(subparsers)
        parser.add_argument('workflow_path', type=str, help="Path to the directory containing the workflow's files")
        return parser

    def run(self, workflow_path, **kwargs):
        return PlatformManager().publish_workflow(workflow_path)
        # TODO: feedback
