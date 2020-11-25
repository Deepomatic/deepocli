import sys
import cv2
import logging
import threading
from text_unidecode import unidecode
from tqdm import tqdm
from ..exceptions import (DeepoCLICredentialsError,
                          SendInferenceError,
                          ResultInferenceError,
                          ResultInferenceTimeout)
from ..common import (SUPPORTED_IMAGE_INPUT_FORMAT, SUPPORTED_IMAGE_OUTPUT_FORMAT,
                      SUPPORTED_PROTOCOLS_INPUT, SUPPORTED_VIDEO_INPUT_FORMAT,
                      SUPPORTED_VIDEO_OUTPUT_FORMAT, Queue, TqdmToLogger)

from ..thread_base import QUEUE_MAX_SIZE, MainLoop, Pool, Thread, Greenlet
from . import parser_helpers
from ..workflow import get_workflow
from ..frame import CurrentFrames
from ..input_data import InputThread, VideoInputData, get_input
from ..output_data import OutputThread


LOGGER = logging.getLogger(__name__)

# Draw parameters
SCORE_DECIMAL_PRECISION = 4             # Prediction score decimal number precision
FONT_SCALE = 0.5                        # Size of the font we draw in the image_output
BOX_COLOR = (255, 0, 0)                 # Bounding box color (BGR)
BACKGROUND_COLOR = (0, 0, 255)          # Text background color (BGR)
TEXT_COLOR = (255, 255, 255)            # Text color (BGR)
TAG_TEXT_CORNER = (10, 10)              # Beginning of text tag column (pixel)
TAG_TEXT_INTERSPACE = 5                 # Vertical space between tags in tag column (pixel)


def substract_tuple(tuple1, tuple2):
    return tuple(x - y for x, y in zip(tuple1, tuple2))


def get_coordinates_from_roi(roi, width, height):
    bbox = roi['bbox']
    xmin = int(bbox['xmin'] * width)
    ymin = int(bbox['ymin'] * height)
    xmax = int(bbox['xmax'] * width)
    ymax = int(bbox['ymax'] * height)
    return (xmin, ymin, xmax, ymax)


class DrawImagePostprocessing(object):

    def __init__(self, **kwargs):
        self._draw_labels = kwargs['draw_labels']
        self._draw_scores = kwargs['draw_scores']

    def __call__(self, frame):
        frame.output_image = frame.image.copy()
        output_image = frame.output_image
        height = output_image.shape[0]
        width = output_image.shape[1]
        tag_drawn = 0  # Used to store the number of tags already drawn
        for pred in frame.predictions['outputs'][0]['labels']['predicted']:
            # Build legend
            label = u''
            if self._draw_labels:
                label = pred['label_name']
            if self._draw_labels and self._draw_scores:
                label += ' '
            if self._draw_scores:
                label += str(round(pred['score'], SCORE_DECIMAL_PRECISION))

            # Make sure labels are ascii because cv2.FONT_HERSHEY_SIMPLEX doesn't support non-ascii
            label = unidecode(label)

            # Get text draw parameters
            ret, baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, 1)

            # If we have a bounding box
            roi = pred.get('roi')
            if roi is not None:
                # Retrieve coordinates
                xmin, ymin, xmax, ymax = get_coordinates_from_roi(roi, width, height)

                # Draw bounding box
                cv2.rectangle(output_image, (xmin, ymin), (xmax, ymax), BOX_COLOR, 1)

                if label != '':
                    # First get ideal corners
                    background_corner1 = (xmin, ymax + 2)
                    background_corner2 = (background_corner1[0] + ret[0], background_corner1[1] + ret[1] + baseline)
                    text_corner = (background_corner1[0], background_corner1[1] + ret[1])

                    # Then make sure they fit in the image
                    # For x-axis, simply shift the box to the left
                    # For y-axis, put the label at the top if it doesn't fit under the box
                    x_offset = max(0, background_corner2[0] - width + 1)
                    if background_corner2[1] > height - 1:
                        y_offset = background_corner2[1] - ymin + 2
                    else:
                        y_offset = 0
                    background_corner1 = substract_tuple(background_corner1, (x_offset, y_offset))
                    background_corner2 = substract_tuple(background_corner2, (x_offset, y_offset))
                    text_corner = substract_tuple(text_corner, (x_offset, y_offset))

                    # Finally draw everything
                    cv2.rectangle(output_image, background_corner1, background_corner2, BACKGROUND_COLOR, -1)
                    cv2.putText(output_image, label, text_corner, cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, TEXT_COLOR, 1)
            elif label != '':
                # First get ideal corners
                if tag_drawn == 0:
                    background_corner1 = TAG_TEXT_CORNER
                else:
                    background_corner1 = (TAG_TEXT_CORNER[0], background_corner2[1] + TAG_TEXT_INTERSPACE)
                background_corner2 = (background_corner1[0] + ret[0], background_corner1[1] + ret[1] + baseline)
                text_corner = (background_corner1[0], background_corner1[1] + ret[1])

                # Finally draw everything
                cv2.rectangle(output_image, background_corner1, background_corner2, BACKGROUND_COLOR, -1)
                cv2.putText(output_image, label, text_corner, cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, TEXT_COLOR, 1)
                tag_drawn += 1


class BlurImagePostprocessing(object):
    def __init__(self, **kwargs):
        self._method = kwargs.get('blur_method', 'pixel')
        self._strength = int(kwargs.get('blur_strength', 10))

    def __call__(self, frame):
        frame.output_image = frame.image.copy()
        output_image = frame.output_image
        height = output_image.shape[0]
        width = output_image.shape[1]
        for pred in frame.predictions['outputs'][0]['labels']['predicted']:
            # Check that we have a bounding box
            roi = pred.get('roi')
            if roi is not None:
                # Retrieve coordinates
                xmin, ymin, xmax, ymax = get_coordinates_from_roi(roi, width, height)

                # Draw
                if self._method == 'black':
                    cv2.rectangle(output_image, (xmin, ymin), (xmax, ymax), (0, 0, 0), -1)
                elif self._method == 'gaussian':
                    rectangle = output_image[ymin:ymax, xmin:xmax]
                    rectangle = cv2.GaussianBlur(rectangle, (0, 0), self._strength)
                    output_image[ymin:ymax, xmin:xmax] = rectangle
                elif self._method == 'pixel':
                    rectangle = output_image[ymin:ymax, xmin:xmax]
                    small = cv2.resize(rectangle, (0, 0),
                                       fx=1. / min((xmax - xmin), self._strength),
                                       fy=1. / min((ymax - ymin), self._strength))
                    rectangle = cv2.resize(small, ((xmax - xmin), (ymax - ymin)),
                                           interpolation=cv2.INTER_NEAREST)
                    output_image[ymin:ymax, xmin:xmax] = rectangle


class PrepareInferenceThread(Thread):
    def process_msg(self, frame):
        try:
            _, buf = cv2.imencode('.jpg', frame.image)
        except Exception as e:
            LOGGER.error('Could not decode image for frame {}: {}'.format(frame, e))
            return None
        buf_bytes = buf.tobytes()
        frame.buf_bytes = buf_bytes
        self.current_messages.add_frame(frame)
        return frame


class SendInferenceGreenlet(Greenlet):
    def __init__(self, exit_event, input_queue, output_queue, current_messages, workflow):
        super(SendInferenceGreenlet, self).__init__(exit_event, input_queue, output_queue, current_messages)
        self.workflow = workflow
        self.push_client = workflow.new_client()

    def close(self):
        self.workflow.close_client(self.push_client)

    def process_msg(self, frame):
        try:
            frame.inference_async_result = self.workflow.infer(frame.buf_bytes, self.push_client, frame.name)
            return frame
        except SendInferenceError as e:
            self.current_messages.forget_frame(frame)
            LOGGER.error('Error sending frame {}: {}'.format(frame, e))
            return None


class ResultInferenceGreenlet(Greenlet):
    def __init__(self, exit_event, input_queue, output_queue, current_messages, workflow, **kwargs):
        super(ResultInferenceGreenlet, self).__init__(exit_event, input_queue, output_queue, current_messages)
        self.workflow = workflow
        self.threshold = kwargs.get('threshold')

    def fill_predictions(self, predictions, new_predicted, new_discarded):
        for prediction in predictions:
            if prediction['score'] >= self.threshold:
                new_predicted.append(prediction)
            else:
                new_discarded.append(prediction)

    def process_msg(self, frame):
        try:
            predictions = frame.inference_async_result.get_predictions(timeout=60)
            if self.threshold is not None:
                # Keep only predictions higher than threshold
                for output in predictions['outputs']:
                    new_predicted = []
                    new_discarded = []
                    labels = output['labels']
                    self.fill_predictions(labels['predicted'], new_predicted, new_discarded)
                    self.fill_predictions(labels['discarded'], new_predicted, new_discarded)
                    labels['predicted'] = new_predicted
                    labels['discarded'] = new_discarded

            frame.predictions = predictions
            return frame
        except ResultInferenceError as e:
            self.current_messages.forget_frame(frame)
            LOGGER.error('Error getting predictions for frame {}: {}'.format(frame, e))
        except ResultInferenceTimeout as e:
            self.current_messages.forget_frame(frame)
            LOGGER.error("Couldn't get predictions in {} seconds. Ignoring frame {}.".format(e.timeout, frame))
        return None


def input_loop(kwargs, postprocessing=None):
    # Adds smartness to fps handling
    #   1) If both input_fps and output_fps are set, then use them as is.
    #   2) If only one of the two is used, make both equal
    #   3) If none is set:
    #       * If the input is not a video, do nothing and use the default DEFAULT_FPS output value
    #       * If the input is a video, use the input fps as the output fps
    if kwargs['input_fps'] and not kwargs['output_fps']:
        kwargs['output_fps'] = kwargs['input_fps']
        LOGGER.info('Input fps of {} specified, but no output fps specified. Using same value for both.'.format(kwargs['input_fps']))
    elif kwargs['output_fps'] and not kwargs['input_fps']:
        kwargs['input_fps'] = kwargs['output_fps']
        LOGGER.info('Output fps of {} specified, but no input fps specified. Using same value for both.'.format(kwargs['output_fps']))

    # Compute inputs now to access actual input fps if it's a video
    inputs = iter(get_input(kwargs.get('input', 0), kwargs))

    # Deal with last case for fps
    if not(kwargs['input_fps']) and not(kwargs['output_fps']) and isinstance(inputs, VideoInputData):
        kwargs['input_fps'] = inputs.get_fps()
        kwargs['output_fps'] = kwargs['input_fps']
        LOGGER.info('Input fps of {} automatically detected, but no output fps specified.'
                    ' Using same value for both.'.format(kwargs['input_fps']))

    # Initialize progress bar
    frame_count = inputs.get_frame_count()
    max_value = int(frame_count) if frame_count >= 0 else None
    tqdmout = TqdmToLogger(LOGGER, level=LOGGER.getEffectiveLevel())
    pbar = tqdm(total=max_value, file=tqdmout, desc='Input processing', smoothing=0)

    # Initialize workflow for mutual use between send inference pool and result inference pool
    try:
        workflow = get_workflow(kwargs)
    except DeepoCLICredentialsError as e:
        LOGGER.error(str(e))
        sys.exit(1)

    # IMPORTANT: maxsize is important, it allows to regulate the pipeline and
    # avoid to pushes too many requests to rabbitmq when we are already waiting for many results

    nb_queue = 2  # input => prepare inference => output
    if workflow:
        nb_queue += 2  # prepare inference => send inference => result inference

    queues = [Queue(maxsize=QUEUE_MAX_SIZE) for _ in range(nb_queue)]

    exit_event = threading.Event()

    current_frames = CurrentFrames()

    pools = [
        Pool(1, InputThread, thread_args=(exit_event, None, queues[0], inputs)),
        # Encode image into jpeg
        Pool(1, PrepareInferenceThread, thread_args=(exit_event, queues[0], queues[1], current_frames)),
    ]

    if workflow:
        pools.extend([
            # Send inference
            Pool(5, SendInferenceGreenlet, thread_args=(exit_event, queues[1], queues[2], current_frames, workflow)),
            # Gather inference predictions from the worker(s)
            Pool(1, ResultInferenceGreenlet, thread_args=(exit_event, queues[2], queues[3], current_frames, workflow),
                 thread_kwargs=kwargs),
        ])

    # Output predictions
    pools.append(Pool(1, OutputThread, thread_args=(exit_event, queues[-1], None, current_frames, pbar.update, postprocessing),
                      thread_kwargs=kwargs))

    loop = MainLoop(pools, queues, pbar, exit_event, current_frames, lambda: workflow.close() if workflow else None)

    try:
        stop_asked = loop.run_forever()
    except Exception:
        loop.cleanup()
        raise

    # If the process encountered an error, the exit code is 1.
    # If the process is interrupted using SIGINT (ctrl + C) or SIGTERM, the queues are emptied and processed by the
    # threads, and the exit code is 0.
    # If SIGINT or SIGTERM is sent again during this shutdown phase, the threads are killed, and the exit code is 2.
    if exit_event.is_set():
        sys.exit(1)
    elif stop_asked >= 2:
        sys.exit(2)


def setup_cmd_line_parsers(inference_parsers):
    inference_parsers['infer'].set_defaults(func=input_loop)
    inference_parsers['noop'].set_defaults(func=input_loop)
    inference_parsers['draw'].set_defaults(func=lambda args:
                                           input_loop(args, DrawImagePostprocessing(**args)))
    inference_parsers['blur'].set_defaults(func=lambda args:
                                           input_loop(args, BlurImagePostprocessing(**args)))

    # Add verbose for all commands
    # TODO: put this in parent parser when infer commands are not in the root parser
    # And remove all calls to add_verbose_argument
    # https://stackoverflow.com/questions/7498595/python-argparse-add-argument-to-multiple-subparsers
    for parser in inference_parsers.values():
        parser_helpers.add_verbose_argument(parser)

    # Define input group for infer draw blur noop
    for cmd in ['infer', 'draw', 'blur', 'noop']:
        # Define argument groups for easier reading
        group = parser_helpers.add_common_cmd_group(inference_parsers[cmd], 'input')
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
        group.add_argument('--no_fps_estimation', dest='measure_fps', action='store_false', help="For stream inputs only, "
                            "estimates the real framerate by measuring the time between each frame.")
        group.add_argument('--skip_frame', type=int, help="Number of frame to skip between two frames from the input."
                           " It can be combined with input_fps", default=0)
        parser_helpers.add_recursive_argument(group)

    output_groups = {}
    # Define output group for infer draw blur noop
    for cmd in ['infer', 'draw', 'blur', 'noop']:
        group = parser_helpers.add_common_cmd_group(inference_parsers[cmd], 'output')
        output_groups[cmd] = group
        group = output_groups[cmd]
        group.add_argument('-o', '--outputs', required=True, nargs='+', help="Output path, either an image (*{}),"
                           " a video (*{}), a json (*.json) or a directory.".format(', *'.join(SUPPORTED_IMAGE_OUTPUT_FORMAT),
                                                                                    ', *'.join(SUPPORTED_VIDEO_OUTPUT_FORMAT)))
        group.add_argument('--output_fps', type=int, help="FPS used for output video reconstruction.", default=None)

    # Define output group for infer draw blur
    for cmd in ['infer', 'draw', 'blur']:
        group = output_groups[cmd]
        group.add_argument('-s', '--studio_format', action='store_true',
                           help="Convert deepomatic run predictions into deepomatic studio format.")

    # Define output group for draw blur noop
    for cmd in ['draw', 'blur', 'noop']:
        group = output_groups[cmd]
        group.add_argument('-F', '--fullscreen', help="Fullscreen if window output.", action="store_true")

    # Define option group for draw blur
    for cmd in ['draw', 'blur']:
        subparser = inference_parsers[cmd]
        subparser.add_argument('--from_file', type=str, dest='pred_from_file',
                               help="Uses prediction from a Vulcan or Studio JSON.")

    # Define model group for infer draw blur
    for cmd in ['infer', 'draw', 'blur']:
        group = inference_parsers[cmd].add_argument_group('model arguments')
        group.add_argument('-r', '--recognition_id', help="Neural network recognition version ID.")
        group.add_argument('-t', '--threshold', type=float, help="Threshold above which a prediction is considered valid.", default=None)

    # Define onprem group for infer draw blur
    for cmd in ['infer', 'draw', 'blur']:
        group = inference_parsers[cmd].add_argument_group('on-premises arguments')
        group.add_argument('-u', '--amqp_url', help="AMQP url for on-premises deployments.")
        group.add_argument('-k', '--routing_key', help="Recognition routing key for on-premises deployments.")

    # Define draw specific options
    group = inference_parsers['draw'].add_argument_group('drawing arguments')
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

    # Define blur specific options
    group = inference_parsers['blur'].add_argument_group('blurring arguments')
    group.add_argument('-M', '--blur_method', help="Blur method to apply, either 'pixel', 'gaussian' or 'black', defaults to 'pixel'.",
                       default='pixel', choices=['pixel', 'gaussian', 'black'])
    group.add_argument('-B', '--blur_strength', help="Blur strength, defaults to 10.", default=10)
