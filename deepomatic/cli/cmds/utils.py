import json
import logging
import argparse
import os
import re

from deepomatic.cli.cmds import parser_helpers
from deepomatic.cli.common import (SUPPORTED_IMAGE_INPUT_FORMAT, SUPPORTED_IMAGE_OUTPUT_FORMAT,
                                   SUPPORTED_PROTOCOLS_INPUT, SUPPORTED_VIDEO_INPUT_FORMAT,
                                   SUPPORTED_VIDEO_OUTPUT_FORMAT, SUPPORTED_FOURCC)

logger = logging.getLogger(__name__)


class Command(object):
    """
        Base command, use docstring to fill the command help
        The next lines are used for filling the command description
    """

    def __init__(self):
        # The name of a command is the Command class name lowercase and - joined in case of camel case
        camel_case_name = self.__class__.__name__.replace("Command", "")
        self.name = re.sub(r'(?<!^)(?=[A-Z])', '-', camel_case_name).lower()
        self.help, _, self.description = self.__class__.__doc__.strip().partition('\n')

    def setup(self, subparsers):
        parser = subparsers.add_parser(self.name, help=self.help, description=self.description)
        parser.set_defaults(func=lambda args: self.run(**args))

        subcommands = [command for command in [getattr(self.__class__, attr) for attr in dir(
            self.__class__)] if isinstance(command, type) and issubclass(command, Command)]
        if subcommands:
            subparser = parser.add_subparsers(dest='{}_command'.format(self.name), help='')
            subparser.required = True
            for subcommand in subcommands:
                subcommand().setup(subparser)
        # add verbose
        parser.add_argument('--verbose', dest='verbose', action='store_true',
                            help='Increase output verbosity.')

        return parser

    def run(self, *args, **kwargs):
        print(type(self).__name__, args, kwargs)


def valid_path(file_path):
    if not os.path.exists(file_path):
        raise argparse.ArgumentTypeError("'{}' file does not exist".format(file_path))
    return file_path


def valid_json(data):
    try:
        return json.loads(data)
    except Exception:
        raise argparse.ArgumentTypeError("'{}' is not a valid JSON".format(data))


class BuildDict(argparse.Action):
    """
    This class is used in argparse. It will transform a chain of name:values into a dict.
    """

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        self._nargs = nargs
        super(BuildDict, self).__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        dic = {}
        for kv in values:
            vals = kv.split(":")
            assert len(vals) == 2
            name = vals[0]
            value = vals[1]
            dic[name] = value
        setattr(namespace, self.dest, dic)


def setup_model_cmd_line_parser(mode, cmd, inference_parsers):
    assert mode in ['site', 'platform']
    assert cmd in ['infer', 'draw', 'blur', 'noop']

    # Define input group for infer draw blur noop
    if cmd in ['infer', 'draw', 'blur', 'noop']:
        # Define argument groups for easier reading
        group = parser_helpers.add_common_cmd_group(inference_parsers, 'input')
        group.add_argument('-i', '--input', required=True,
                           help="Input path, either an image (*{}), a video (*{}), a directory, a stream (*{}),"
                           " or a Studio format (*.txt). If the given path is a directory,"
                           " it will recursively run inference on all the supported files"
                           " in this directory if the -R option is used.".format(', *'.join(SUPPORTED_IMAGE_INPUT_FORMAT),
                                                                                 ', *'.join(SUPPORTED_VIDEO_INPUT_FORMAT),
                                                                                 ', *'.join(SUPPORTED_PROTOCOLS_INPUT)))
        group.add_argument('--input_fps', type=int, help="FPS used for input video frame skipping and extraction."
                           " If higher than the original video FPS, all frames will be analysed only once having"
                           " the same effect as not using this parameter. If lower than the original video FPS,"
                           " some frames will be discarded to simulate an input of the given FPS.", default=None)
        group.add_argument('--skip_frame', type=int, help="Number of frame to skip between two frames from the input."
                           " It can be combined with input_fps", default=0)
        parser_helpers.add_recursive_argument(group)

    output_groups = {}
    # Define output group for infer draw blur noop
    if cmd in ['infer', 'draw', 'blur', 'noop']:
        group = parser_helpers.add_common_cmd_group(inference_parsers, 'output')
        output_groups[cmd] = group
        group = output_groups[cmd]
        group.add_argument('-o', '--outputs', required=True, nargs='+', help="Output path, either an image (*{}),"
                           " a video (*{}), a json (*.json) or a directory.".format(', *'.join(SUPPORTED_IMAGE_OUTPUT_FORMAT),
                                                                                    ', *'.join(SUPPORTED_VIDEO_OUTPUT_FORMAT)))
        group.add_argument('--output_fps', type=int, help="FPS used for output video reconstruction.", default=None)
        group.add_argument('--fourcc', type=str, help="Codec used for output video reconstruction.",
                           choices=set([fourcc for fourccs in SUPPORTED_FOURCC.values() for fourcc in fourccs]), default=None)

    # Define output group for draw blur noop
    if cmd in ['draw', 'blur', 'noop']:
        group = output_groups[cmd]
        group.add_argument('-F', '--fullscreen', help="Fullscreen if window output.", action="store_true")

    # Define option group for draw blur
    if cmd in ['draw', 'blur']:
        subparser = inference_parsers
        subparser.add_argument('--from_file', type=str, dest='pred_from_file',
                               help="Uses prediction from a Vulcan JSON")

    # Define model group for infer draw blur
    if cmd in ['infer', 'draw', 'blur']:
        group = inference_parsers.add_argument_group('model arguments')
        reco_required = (mode == 'platform')
        group.add_argument('-r', '--recognition_id', required=reco_required,
                           help="Neural network recognition version ID.")
        group.add_argument('-t', '--threshold', type=float,
                           help="Threshold above which a prediction is considered valid.",
                           default=None)

    # Define onprem group for infer draw blur
    if mode == "site" and cmd in ['infer', 'draw', 'blur']:
        group = inference_parsers.add_argument_group('on-premises arguments')
        group.add_argument('-u', '--amqp_url', required=True,
                           help="AMQP url for on-premises deployments.")
        group.add_argument('-k', '--routing_key', required=True,
                           help="Recognition routing key for on-premises deployments.")

    if cmd == "draw":
        # Define draw specific options
        group = inference_parsers.add_argument_group('drawing arguments')
        group.add_argument('-fs', '--font_scale', dest='font_scale', type=float,
                           help="Text font scale, defaults to 0.5",
                           default=0.5)
        group.add_argument('-ft', '--font_thickness', dest='font_thickness', type=int,
                           help="Text font thickness, must be an int and defaults to 1",
                           default=1)
        group.add_argument('--font_bg_color', default=None, nargs=3,
                           help="Expect a B G R value. If set, draws labels with a unique background color."
                                " By default, the background is red/orange/green depending on the threshold set"
                                " and the prediction score.", type=int)
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

    if cmd == "blur":
        # Define blur specific options
        group = inference_parsers.add_argument_group('blurring arguments')
        group.add_argument('-M', '--blur_method', help="Blur method to apply, either 'pixel', 'gaussian' or 'black', defaults to 'pixel'.",
                           default='pixel', choices=['pixel', 'gaussian', 'black'])
        group.add_argument('-B', '--blur_strength', help="Blur strength, defaults to 10.", default=10)
