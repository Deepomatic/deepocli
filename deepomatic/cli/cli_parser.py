import sys
import argparse
from deepomatic.cli.cmds.infer import main as infer
from deepomatic.cli.cmds.draw import main as draw
from deepomatic.cli.cmds.feedback import main as feedback
from deepomatic.cli.cmds.blur import main as blur
from deepomatic.cli.io_data import ImageInputData, VideoInputData, StreamInputData


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
    subparsers = argparser.add_subparsers(dest='command', help='')
    subparsers.required = True

    infer_parser = subparsers.add_parser('infer', help="Computes prediction on a file or directory and outputs results as a JSON file.")
    infer_parser.set_defaults(func=infer)

    draw_parser = subparsers.add_parser('draw', help="Generates new images and videos with predictions results drawn on them. Computes prediction if JSON has not yet been generated.")
    draw_parser.set_defaults(func=draw)

    blur_parser = subparsers.add_parser('blur', help="Generates new images and videos with predictions results blurred on them. Computes prediction if JSON has not yet been generated.")
    blur_parser.set_defaults(func=blur)

    feedback_parser = subparsers.add_parser('feedback', help='Uploads images from the local machine to Deepomatic Studio.')
    feedback_parser.set_defaults(func=feedback, recursive=False)

    parsers = [infer_parser, draw_parser, blur_parser]
    for parser in parsers:
        parser.add_argument('-i', '--input', required=True, help="Path on which inference should be run. It can be an image (supported formats: *{}), a video (supported formats: *{}) or a directory. If the given path is a directory, it will recursively run inference on all the supported files in this directory.".format(', *'.join(ImageInputData.supported_formats), ', *'.join(VideoInputData.supported_formats)))
        parser.add_argument('-o', '--output', required=True, help="Path in which output should be written. It can be an image (supported formats: *{}), a video (supported formats: *{}) or a directory.".format(', *'.join(ImageInputData.supported_formats), ', *'.join(VideoInputData.supported_formats)))
        parser.add_argument('-r', '--recognition_id', required=True, help="Neural network recognition version ID.")
        parser.add_argument('-u', '--amqp_url', help="AMQP url for on-premises deployments.")
        parser.add_argument('-k', '--routing_key', help="Recognition routing key for on-premises deployments.")
        parser.add_argument('-t', '--threshold', help="Threshold above which a prediction is considered valid.", default=0.7)
        parser.add_argument('--output_fps', help="In case of video output, video frame rate.", default=25)
        parser.add_argument('--fullscreen', help="Fullscreen if window output.", action="store_true")

    draw_parser.add_argument('--draw_scores', help="Overlays the prediction scores.", action="store_true")
    draw_parser.add_argument('--draw_labels', help="Overlays the prediction labels.", action="store_true")

    blur_parser.add_argument('--blur_method', help="Blur method to apply, either 'pixel', 'gaussian' or 'black', defaults to 'pixel'.", default='pixel', choices=['pixel', 'gaussian', 'black'])
    blur_parser.add_argument('--blur_strength', help="Blur strength, defaults to 10.", default=10)

    feedback_parser.add_argument('-d', '--dataset', required=True, help="Deepomatic Studio dataset name.", type=str)
    feedback_parser.add_argument('-o', '--organization', required=True, help="Deepomatic Studio organization slug.", type=str)
    feedback_parser.add_argument('path', type=str, nargs='+', help='Path to an image file, images directory or json file or directory.')
    feedback_parser.add_argument('--recursive', dest='recursive', action='store_true', help='Goes through all files in subdirectories.')
    feedback_parser.add_argument('--json', dest='json_file', action='store_true', help='Look for JSON files instead of images.')

    return argparser

def run(args):
    # Initialize the argparser
    argparser = argparser_init()

    # Display the help section if no arguments are supplied
    if len(args) == 0:
        argparser.print_help(sys.stderr)
        sys.exit(1)
    # Otherwise parse the arguments and run the command
    else:
        args = argparser.parse_args(args)
        args.func(vars(args))
