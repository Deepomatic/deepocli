from deepomatic.cli.cmds.utils import Command
from ..utils import InferManager
from deepomatic.cli.cmds.utils import setup_model_cmd_line_parser


class NoopCommand(Command):
    """
        Does nothing but reading the input and outputting it in the specified format, without predictions.
        Typical usage is: deepo platform model noop -i 0 -o window
    """

    def setup(self, subparsers):
        parser = super(NoopCommand, self).setup(subparsers)
        setup_model_cmd_line_parser("platform", "noop", parser)
        return parser

    def run(self, **kwargs):
        return InferManager().input_loop(kwargs)
