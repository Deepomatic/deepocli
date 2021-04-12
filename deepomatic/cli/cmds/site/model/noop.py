from deepomatic.cli.cmds.utils import Command
from deepomatic.cli.lib.inference import InferManager
from deepomatic.cli.cmds.utils import setup_model_cmd_line_parser


class NoopCommand(Command):
    """
        Does nothing but reading the input and outputting it in the specified format, without predictions.
        Typical usage is: deepo site model noop -i 0 -o window
    """

    def setup(self, subparsers):
        parser = super(NoopCommand, self).setup(subparsers)
        setup_model_cmd_line_parser("site", "noop", parser)
        return parser

    def run(self, **kwargs):
        return InferManager().input_loop(kwargs)
