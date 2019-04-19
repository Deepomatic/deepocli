import sys
import argparse
from .cmds.feedback import main as feedback
from .input_data import ImageInputData, VideoInputData, StreamInputData, input_loop
from .cmds.infer import BlurImagePostprocessing, DrawImagePostprocessing
from .version import __version__, __title__


class ParserWithHelpOnError(argparse.ArgumentParser):
    """
    Modifies argparser to display the help whenever an error is triggered.
    """
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(1)


def argparser_init():
    argparser = ParserWithHelpOnError(prog='deepo')
    argparser.add_argument(
        '-v', '--version', action='version',
        version='{title} {version}'.format(title=__title__, version=__version__)
    )
    subparsers = argparser.add_subparsers(dest='command', help='')
    subparsers.required = True

    infer_parser = subparsers.add_parser('infer', help="Computes prediction on a file or directory and outputs results as a JSON file.")
    infer_parser.set_defaults(func=input_loop)

    draw_parser = subparsers.add_parser('draw', help="Generates new images and videos with predictions results drawn on them. Computes prediction if JSON has not yet been generated.")
    draw_parser.set_defaults(func=lambda args: input_loop(args, DrawImagePostprocessing(**args)))

    blur_parser = subparsers.add_parser('blur', help="Generates new images and videos with predictions results blurred on them. Computes prediction if JSON has not yet been generated.")
    blur_parser.set_defaults(func=lambda args: input_loop(args, BlurImagePostprocessing(**args)))

    studio_parser = subparsers.add_parser('studio', help='Deepomatic Studio related commands')
    studio_subparser = studio_parser.add_subparsers(dest='studio_command', help='')
    studio_subparser.required = True
    add_images_parser = studio_subparser.add_parser('add_images', help='Uploads images from the local machine to Deepomatic Studio.')
    add_images_parser.set_defaults(func=feedback, recursive=False)

    for parser in [infer_parser, draw_parser, blur_parser, add_images_parser]:
        parser.add_argument('-R', '--recursive', dest='recursive', action='store_true', help='If a directory input is used, goes through all files in subdirectories.')

    for parser in [infer_parser, draw_parser, blur_parser]:
        parser.add_argument('-i', '--input', required=True, help="Path on which inference should be run. It can be an image (supported formats: *{}), a video (supported formats: *{}) or a directory. If the given path is a directory, it will recursively run inference on all the supported files in this directory.".format(', *'.join(ImageInputData.supported_formats), ', *'.join(VideoInputData.supported_formats)))
        parser.add_argument('-o', '--outputs', required=True, nargs='+', help="Path in which output should be written. It can be an image (supported formats: *{}), a video (supported formats: *{}) or a directory.".format(', *'.join(ImageInputData.supported_formats), ', *'.join(VideoInputData.supported_formats)))
        parser.add_argument('-r', '--recognition_id', required=True, help="Neural network recognition version ID.")
        parser.add_argument('-u', '--amqp_url', help="AMQP url for on-premises deployments.")
        parser.add_argument('-k', '--routing_key', help="Recognition routing key for on-premises deployments.")
        parser.add_argument('-t', '--threshold', type=float, help="Threshold above which a prediction is considered valid.", default=None)
        parser.add_argument('--input_fps', type=int, help="FPS used for input video frame skipping and extraction. If higher than the original video FPS, all frames will be analysed only once having the same effect as not using this parameter. If lower than the original video FPS, some frames will be discarded to simulate an input of the given FPS.", default=None)
        parser.add_argument('--skip_frame', type=int, help="Number of frame to skip between two frames from the input. It can be combined with input_fps", default=0)
        parser.add_argument('--output_fps', type=int, help="FPS usef for output video reconstruction.", default=None)
        parser.add_argument('-s', '--studio_format', action='store_true', help="Convert deepomatic run predictions into deepomatic studio format.")

    for parser in [draw_parser, blur_parser]:
        parser.add_argument('-F', '--fullscreen', help="Fullscreen if window output.", action="store_true")

    draw_parser.add_argument('-S', '--draw_scores', help="Overlays the prediction scores.", action="store_true")
    draw_parser.add_argument('-L', '--draw_labels', help="Overlays the prediction labels.", action="store_true")

    blur_parser.add_argument('-M', '--blur_method', help="Blur method to apply, either 'pixel', 'gaussian' or 'black', defaults to 'pixel'.", default='pixel', choices=['pixel', 'gaussian', 'black'])
    blur_parser.add_argument('-B', '--blur_strength', help="Blur strength, defaults to 10.", default=10)

    add_images_parser.add_argument('-d', '--dataset', required=True, help="Deepomatic Studio dataset name.", type=str)
    add_images_parser.add_argument('-o', '--organization', required=True, help="Deepomatic Studio organization slug.", type=str)
    add_images_parser.add_argument('path', type=str, nargs='+', help='Path to an image file, images directory or json file or directory.')
    add_images_parser.add_argument('--json', dest='json_file', action='store_true', help='Look for JSON files instead of images.')

    return argparser


def run(args):
    # Initialize the argparser
    argparser = argparser_init()
    args = argparser.parse_args(args)
    return args.func(vars(args))
