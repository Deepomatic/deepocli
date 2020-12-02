from deepomatic.cli.cmds import parser_helpers
from deepomatic.cli.common import (SUPPORTED_IMAGE_INPUT_FORMAT, SUPPORTED_IMAGE_OUTPUT_FORMAT,
                                   SUPPORTED_PROTOCOLS_INPUT, SUPPORTED_VIDEO_INPUT_FORMAT,
                                   SUPPORTED_VIDEO_OUTPUT_FORMAT)


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
