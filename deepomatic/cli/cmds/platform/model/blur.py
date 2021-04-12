from deepomatic.cli.cmds.utils import Command
from ..utils import InferManager, BlurImagePostprocessing
from deepomatic.cli.cmds.utils import setup_model_cmd_line_parser


class BlurCommand(Command):
    """
        Generates new images and videos with predictions results blurred on them. Computes prediction if JSON has not yet been generated.
        Typical usage is: deepo platform model blur -i img.png -o pred.json draw.png -r 12345
    """

    def setup(self, subparsers):
        parser = super(BlurCommand, self).setup(subparsers)

        setup_model_cmd_line_parser("platform", "blur", parser)
        return parser

    def run(self, **kwargs):
        return InferManager().input_loop(kwargs, BlurImagePostprocessing(**kwargs))
