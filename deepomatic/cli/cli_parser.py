import os
import sys
import logging
import argparse
from .cmds import infer, studio, camera
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
    # Initialize main argparser and version command
    argparser = ParserWithHelpOnError(prog='deepo')
    argparser.add_argument(
        '-v', '--version', action='version',
        version='{title} {version}'.format(title=__title__, version=__version__)
    )

    subparsers = argparser.add_subparsers(dest='command', help='')
    subparsers.required = True

    inference_parsers = {}
    # Initialize subparser: infer
    help_msg = "Computes prediction on a file or directory and outputs results as a JSON file."
    desc_mgs = help_msg + " Typical usage is: deepo infer -i img.png -o pred.json -r 12345"
    inference_parsers['infer'] = subparsers.add_parser('infer', help=help_msg, description=desc_mgs)

    # Initialize subparser: noop
    help_msg = "Does nothing but reading the input and outputting it in the specified format, without predictions."
    desc_mgs = help_msg + " Typical usage is: deepo noop -i 0 -o window"
    inference_parsers['noop'] = subparsers.add_parser('noop', help=help_msg, description=desc_mgs)

    # Initialize subparser: draw
    help_msg = ("Generates new images and videos with predictions results drawn on them."
                " Computes prediction if JSON has not yet been generated.")
    desc_mgs = help_msg + " Typical usage is: deepo draw -i img.png -o pred.json draw.png -r 12345"
    inference_parsers['draw'] = subparsers.add_parser('draw', help=help_msg, description=desc_mgs)

    # Initialize subparser: blur
    help_msg = ("Generates new images and videos with predictions results blurred on them."
                " Computes prediction if JSON has not yet been generated.")
    desc_mgs = help_msg + " Typical usage is: deepo blur -i img.png -o pred.json draw.png -r 12345"
    inference_parsers['blur'] = subparsers.add_parser('blur', help=help_msg, description=desc_mgs)

    # TODO: infer, draw, blur and noop should be in a common command (like studio and cameras)
    infer.setup_cmd_line_parsers(inference_parsers)

    # Initialize subparser: studio
    help_msg = "Deepomatic Studio related commands"
    studio_parser = subparsers.add_parser('studio', help=help_msg, description=help_msg)
    studio_subparser = studio_parser.add_subparsers(dest='studio_command', help='')
    studio_subparser.required = True
    studio.setup_cmd_line_subparser(studio_subparser)

    # Initialize subparser: camera
    help_msg = "Camera server related commands"
    camera_parser = subparsers.add_parser('camera', help=help_msg, description=help_msg)
    camera_subparser = camera_parser.add_subparsers(dest='camera_command', help='')
    camera_subparser.required = True
    camera.setup_cmd_line_subparser(camera_subparser)

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
