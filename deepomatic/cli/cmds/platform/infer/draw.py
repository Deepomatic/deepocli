from deepomatic.cli.cmds.utils import Command
from ..utils import InferManager, DrawImagePostprocessing
from .utils import setup_cmd_line_parsers


class DrawCommand(Command):
    """
        Generates new images and videos with predictions results drawn on them. Computes prediction if JSON has not yet been generated.
        Typical usage is: deepo draw -i img.png -o pred.json draw.png -r 12345
    """

    def setup(self, subparsers):
        parser = super(DrawCommand, self).setup(subparsers)
        setup_cmd_line_parsers("draw", parser)
        # Define draw specific options
        group = parser.add_argument_group('drawing arguments')
        score_group = group.add_mutually_exclusive_group()
        score_group.add_argument('-S', '--draw_scores', dest='draw_scores', help="Overlay the prediction scores. Default behavior.",
                                 action="store_true")
        score_group.add_argument('--no_draw_scores', dest='draw_scores', help="Do not overlay the prediction scores.", action="store_false")
        score_group.set_defaults(draw_scores=True)
        label_group = group.add_mutually_exclusive_group()
        label_group.add_argument('-L', '--draw_labels', dest='draw_labels', help="Overlay the prediction labels. Default behavior.",
                                 action="store_true")
        label_group.add_argument('--no_draw_labels', dest='draw_labels', help="Do not overlay the prediction labels.", action="store_false")
        label_group.set_defaults(draw_labels=True)

        return parser

    def run(self, **kwargs):
        return InferManager().input_loop(kwargs, DrawImagePostprocessing(**kwargs))
