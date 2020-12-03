import logging
import argparse
import os
import re

from deepomatic.cli.cmds import parser_helpers
from deepomatic.cli.common import (SUPPORTED_IMAGE_INPUT_FORMAT, SUPPORTED_IMAGE_OUTPUT_FORMAT,
                                   SUPPORTED_PROTOCOLS_INPUT, SUPPORTED_VIDEO_INPUT_FORMAT,
                                   SUPPORTED_VIDEO_OUTPUT_FORMAT)

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
            subparser = parser.add_subparsers(dest='{} command'.format(self.name), help='')
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
        raise IOError("'{}' file does not exist".format(file_path))
    return file_path


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


def setup_cmd_line_parsers(cmd, inference_parsers):
    # Define input group for infer draw blur noop
    if cmd in ['infer', 'draw', 'blur', 'noop']:
        # Define argument groups for easier reading
        group = parser_helpers.add_common_cmd_group(inference_parsers, 'input')
        group.add_argument('-i', '--input', required=True,
                           help="Input path, either an image (*{}), a video (*{}), a directory, a stream (*{}),"
                           " or a Studio json (*.json). If the given path is a directory,"
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

    # Define output group for infer draw blur
    if cmd in ['infer', 'draw', 'blur']:
        group = output_groups[cmd]
        group.add_argument('-s', '--studio_format', action='store_true',
                           help="Convert deepomatic run predictions into deepomatic studio format.")

    # Define output group for draw blur noop
    if cmd in ['draw', 'blur', 'noop']:
        group = output_groups[cmd]
        group.add_argument('-F', '--fullscreen', help="Fullscreen if window output.", action="store_true")

    # Define option group for draw blur
    if cmd in ['draw', 'blur']:
        subparser = inference_parsers
        subparser.add_argument('--from_file', type=str, dest='pred_from_file',
                               help="Uses prediction from a Vulcan or Studio JSON.")

    # Define model group for infer draw blur
    if cmd in ['infer', 'draw', 'blur']:
        group = inference_parsers.add_argument_group('model arguments')
        group.add_argument('-r', '--recognition_id', help="Neural network recognition version ID.")
        group.add_argument('-t', '--threshold', type=float, help="Threshold above which a prediction is considered valid.", default=None)

    # Define onprem group for infer draw blur
    if cmd in ['infer', 'draw', 'blur']:
        group = inference_parsers.add_argument_group('on-premises arguments')
        group.add_argument('-u', '--amqp_url', help="AMQP url for on-premises deployments.")
        group.add_argument('-k', '--routing_key', help="Recognition routing key for on-premises deployments.")
