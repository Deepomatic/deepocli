from deepomatic.cli.cmds.utils import Command
from deepomatic.cli.lib.inference import InferManager, DrawImagePostprocessing
from deepomatic.cli.cmds.utils import setup_model_cmd_line_parser


class DrawCommand(Command):
    """
        Generates new images and videos with predictions results drawn on them. Computes prediction if JSON has not yet been generated.
        Typical usage is: deepo site model draw -i img.png -o pred.json draw.png -r 12345
    """

    def setup(self, subparsers):
        parser = super(DrawCommand, self).setup(subparsers)
        setup_model_cmd_line_parser("site", "draw", parser)
        return parser

    def run(self, **kwargs):
        return InferManager().input_loop(kwargs, DrawImagePostprocessing(**kwargs))
