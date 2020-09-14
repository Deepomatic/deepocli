from ...utils import Command
from ..utils import PlatformManager


class InferCommand(Command):
    """
        Test the workflow using Deepomatic API
    """

    def setup(self, subparsers):
        parser = super(InferCommand, self).setup(subparsers)
        parser.add_argument('input', type=str, help="")
        return parser

    def run(self, input, **kwargs):
        return PlatformManager().infer(input)
