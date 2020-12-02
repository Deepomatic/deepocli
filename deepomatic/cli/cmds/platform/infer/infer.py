from deepomatic.cli.cmds.utils import Command
from ..utils import InferManager
from .utils import setup_cmd_line_parsers


class InferCommand(Command):
    """
        Computes prediction on a file or directory and outputs results as a JSON file.
        Typical usage is: deepo infer -i img.png -o pred.json -r 12345
    """

    def setup(self, subparsers):
        parser = super(InferCommand, self).setup(subparsers)
        setup_cmd_line_parsers("infer", parser)
        return parser

    def run(self, kwargs):
        return InferManager().input_loop(kwargs)
