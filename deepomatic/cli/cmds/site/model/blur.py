from deepomatic.cli.cmds.utils import Command
from deepomatic.cli.lib.inference import InferManager, BlurImagePostprocessing
from deepomatic.cli.cmds.utils import setup_model_cmd_line_parser


class BlurCommand(Command):
    """
        Generates new images and videos with predictions results blurred on them. Computes prediction if JSON has not yet been generated.
        Typical usage is: deepo blur -i img.png -o pred.json draw.png -r 12345
    """

    def setup(self, subparsers):
        parser = super(BlurCommand, self).setup(subparsers)

        setup_model_cmd_line_parser("blur", parser)
        # Define blur specific options
        group = parser.add_argument_group('blurring arguments')
        group.add_argument('-M', '--blur_method', help="Blur method to apply, either 'pixel', 'gaussian' or 'black', defaults to 'pixel'.",
                           default='pixel', choices=['pixel', 'gaussian', 'black'])
        group.add_argument('-B', '--blur_strength', help="Blur strength, defaults to 10.", default=10)
        return parser

    def run(self, **kwargs):
        return InferManager().input_loop(kwargs, BlurImagePostprocessing(**kwargs))
