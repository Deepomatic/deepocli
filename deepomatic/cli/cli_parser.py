import os
import sys
import logging
import argparse
from .cmds.feedback import main as feedback
from .input_data import input_loop
from .cmds.infer import BlurImagePostprocessing, DrawImagePostprocessing
from .version import __version__, __title__
from .common import SUPPORTED_IMAGE_OUTPUT_FORMAT, SUPPORTED_VIDEO_OUTPUT_FORMAT, SUPPORTED_IMAGE_INPUT_FORMAT, SUPPORTED_VIDEO_INPUT_FORMAT, SUPPORTED_PROTOCOLS_INPUT, SUPPORTED_FILE_INPUT_FORMAT


class ParserWithHelpOnError(argparse.ArgumentParser):
    """
    Modifies argparser to display the help whenever an error is triggered.
    """
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(1)


def argparser_init():
    # Initialize main argparser and version command
    argparser = ParserWithHelpOnError(prog='deepo')
    argparser.add_argument(
        '-v', '--version', action='version',
        version='{title} {version}'.format(title=__title__, version=__version__)
    )
    subparsers = argparser.add_subparsers(dest='command', help='')
    subparsers.required = True
    subparsers_dict = {}

    # Initialize subparser: infer
    help_msg = "Computes prediction on a file or directory and outputs results as a JSON file."
    desc_mgs = help_msg + " Typical usage is: deepo infer -i img.png -o pred.json -r 12345"
    infer_parser = subparsers.add_parser('infer', help=help_msg, description=desc_mgs)
    infer_parser.set_defaults(func=input_loop)
    subparsers_dict['infer'] = infer_parser

    # Initialize subparser: draw
    help_msg = "Generates new images and videos with predictions results drawn on them. Computes prediction if JSON has not yet been generated."
    desc_mgs = help_msg + " Typical usage is: deepo draw -i img.png -o pred.json draw.png -r 12345"
    draw_parser = subparsers.add_parser('draw', help=help_msg, description=desc_mgs)
    draw_parser.set_defaults(func=lambda args: input_loop(args, DrawImagePostprocessing(**args)))
    subparsers_dict['draw'] = draw_parser

    # Initialize subparser: blur
    help_msg = "Generates new images and videos with predictions results blurred on them. Computes prediction if JSON has not yet been generated."
    desc_mgs = help_msg + " Typical usage is: deepo blur -i img.png -o pred.json draw.png -r 12345"
    blur_parser = subparsers.add_parser('blur', help=help_msg, description=desc_mgs)
    blur_parser.set_defaults(func=lambda args: input_loop(args, BlurImagePostprocessing(**args)))
    subparsers_dict['blur'] = blur_parser

    # Initialize subparser: studio add_images
    help_msg = "Deepomatic Studio related commands"
    studio_parser = subparsers.add_parser('studio', help=help_msg, description=help_msg)
    studio_subparser = studio_parser.add_subparsers(dest='studio_command', help='')
    studio_subparser.required = True
    help_msg = "Uploads images from the local machine to Deepomatic Studio."
    desc_mgs = help_msg + " Typical usage is: deepo studio add_images -i img.png -d mydataset -o myorg"
    add_images_parser = studio_subparser.add_parser('add_images', help=help_msg, description=desc_mgs)
    add_images_parser.set_defaults(func=feedback, recursive=False)
    subparsers_dict['add_images'] = add_images_parser

    # Define argument groups for easier reading
    input_groups = {cmd: subparsers_dict[cmd].add_argument_group('Input parameters') for cmd in ['infer', 'draw', 'blur', 'add_images']}
    output_groups = {cmd: subparsers_dict[cmd].add_argument_group('Output parameters') for cmd in ['infer', 'draw', 'blur']}
    model_groups = {cmd: subparsers_dict[cmd].add_argument_group('Model parameters') for cmd in ['infer', 'draw', 'blur']}
    onprem_groups = {cmd: subparsers_dict[cmd].add_argument_group('On-premises parameters') for cmd in ['infer', 'draw', 'blur']}
    option_groups = {cmd: subparsers_dict[cmd].add_argument_group('Option parameters') for cmd in ['infer', 'draw', 'blur', 'add_images']}

    # Define input group  for infer draw blur
    for cmd in ['infer', 'draw', 'blur']:
        group = input_groups[cmd]
        group.add_argument('-i', '--input', required=True, help="Input path, either an image (*{}), a video (*{}), a directory, a stream (*{}), or a Studio json (*.json). If the given path is a directory, it will recursively run inference on all the supported files in this directory if the -R option is used.".format(', *'.join(SUPPORTED_IMAGE_INPUT_FORMAT), ', *'.join(SUPPORTED_VIDEO_INPUT_FORMAT), ', *'.join(SUPPORTED_PROTOCOLS_INPUT)))
        group.add_argument('--input_fps', type=int, help="FPS used for input video frame skipping and extraction. If higher than the original video FPS, all frames will be analysed only once having the same effect as not using this parameter. If lower than the original video FPS, some frames will be discarded to simulate an input of the given FPS.", default=None)
        group.add_argument('--skip_frame', type=int, help="Number of frame to skip between two frames from the input. It can be combined with input_fps", default=0)

    # Define output group for infer draw blur
    for cmd in ['infer', 'draw', 'blur']:
        group = output_groups[cmd]
        group.add_argument('-o', '--outputs', required=True, nargs='+', help="Output path, either an image (*{}), a video (*{}), a json (*.json) or a directory.".format(', *'.join(SUPPORTED_IMAGE_OUTPUT_FORMAT), ', *'.join(SUPPORTED_VIDEO_OUTPUT_FORMAT)))
        group.add_argument('--output_fps', type=int, help="FPS used for output video reconstruction.", default=None)
        group.add_argument('-s', '--studio_format', action='store_true', help="Convert deepomatic run predictions into deepomatic studio format.")

    # Define output group for draw blur
    for cmd in ['draw', 'blur']:
        group = output_groups[cmd]
        group.add_argument('-F', '--fullscreen', help="Fullscreen if window output.", action="store_true")

    # Define option group for draw blur
    for cmd in ['draw', 'blur']:
        group = option_groups[cmd]
        group.add_argument('--from_file', type=str, dest='pred_from_file', help="Uses prediction from a Vulcan or Studio JSON.")

    # Define model group for infer draw blur
    for cmd in ['infer', 'draw', 'blur']:
        group = model_groups[cmd]
        group.add_argument('-r', '--recognition_id', required=True, help="Neural network recognition version ID.")
        group.add_argument('-t', '--threshold', type=float, help="Threshold above which a prediction is considered valid.", default=None)

    # Define onprem group for infer draw blur
    for cmd in ['infer', 'draw', 'blur']:
        group = onprem_groups[cmd]
        group.add_argument('-u', '--amqp_url', help="AMQP url for on-premises deployments.")
        group.add_argument('-k', '--routing_key', help="Recognition routing key for on-premises deployments.")

    # Define draw specific options
    group = draw_parser.add_argument_group('Drawing parameters')
    group.add_argument('-S', '--draw_scores', help="Overlays the prediction scores.", action="store_true")
    group.add_argument('-L', '--draw_labels', help="Overlays the prediction labels.", action="store_true")

    # Define blur specific options
    group = blur_parser.add_argument_group('Blurring parameters')
    group.add_argument('-M', '--blur_method', help="Blur method to apply, either 'pixel', 'gaussian' or 'black', defaults to 'pixel'.", default='pixel', choices=['pixel', 'gaussian', 'black'])
    group.add_argument('-B', '--blur_strength', help="Blur strength, defaults to 10.", default=10)

    # Define studio group for add_images
    group = add_images_parser.add_argument_group('Studio parameters')
    group.add_argument('-d', '--dataset', required=True, help="Deepomatic Studio dataset name.", type=str)
    group.add_argument('-o', '--organization', required=True, help="Deepomatic Studio organization slug.", type=str)

    # Define input group for add_images
    input_groups['add_images'].add_argument('-i', '--input', type=str, nargs='+', required=True, help="One or several input path, either an image or video file (*{}), a directory, or a Studio or Vulcan json (*.json).".format(', *'.join(SUPPORTED_FILE_INPUT_FORMAT)))
    input_groups['add_images'].add_argument('--json', dest='json_file', action='store_true', help='Look for JSON files instead of images.')
    option_groups['add_images'].add_argument('--set_metadata_path', dest='set_metadata_path', action='store_true', help='Add the relative path as metadata.')

    # Define input groupe for infer draw blur add_images
    for cmd in ['infer', 'draw', 'blur', 'add_images']:
        group = input_groups[cmd]
        group.add_argument('-R', '--recursive', dest='recursive', action='store_true', help='If a directory input is used, goes through all files in subdirectories.')

    # Define option group for infer draw blur add_images
    for cmd in ['infer', 'draw', 'blur', 'add_images']:
        group = option_groups[cmd]
        group.add_argument('--verbose', dest='verbose', action='store_true', help='Increase output verbosity.')

    return argparser


def run(args):
    # Initialize the argparser
    argparser = argparser_init()
    args = argparser.parse_args(args)

    # Update the log level accordingly
    if args.verbose:
        log_level = logging.DEBUG
        log_format = '[%(levelname)s %(name)s %(asctime)s %(process)d %(thread)d %(filename)s:%(lineno)s] %(message)s'
    else:
        log_level = os.getenv('DEEPOMATIC_LOG_LEVEL', logging.INFO)
        log_format = '[%(levelname)s %(asctime)s] %(message)s'
    logging.basicConfig(level=log_level, format=log_format)

    return args.func(vars(args))
