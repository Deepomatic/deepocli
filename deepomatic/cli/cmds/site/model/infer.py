from deepomatic.cli.cmds.utils import Command
from deepomatic.cli.lib.inference import InferManager
from deepomatic.cli.cmds.utils import setup_model_cmd_line_parser


class InferCommand(Command):
    """
        Computes prediction on a file or directory and outputs results as a JSON file.
        Typical usage is: deepo site model infer -i img.png -o pred.json -r 12345
    """

    def setup(self, subparsers):
        parser = super(InferCommand, self).setup(subparsers)
        setup_model_cmd_line_parser("site", "infer", parser)
        return parser

    def run(self, **kwargs):
        return InferManager().input_loop(kwargs)
