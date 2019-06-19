import os
import cv2
import sys
import json
import logging
import threading
from .exceptions import DeepoCLICredentialsError
from .thread_base import Pool, Thread, MainLoop, CurrentMessages, blocking_lock, QUEUE_MAX_SIZE
from .cmds.infer import SendInferenceGreenlet, ResultInferenceGreenlet, PrepareInferenceThread
from tqdm import tqdm
from .common import TqdmToLogger, Queue, LifoQueue, clear_queue, SUPPORTED_IMAGE_INPUT_FORMAT, SUPPORTED_VIDEO_INPUT_FORMAT, SUPPORTED_PROTOCOLS_INPUT
from threading import Lock
from .workflow import get_workflow
from .output_data import OutputThread
from .frame import Frame, CurrentFrames
from .cmds.studio_helpers.vulcan2studio import transform_json_from_vulcan_to_studio


LOGGER = logging.getLogger(__name__)


def get_input(descriptor, kwargs):
    if descriptor is None:
        LOGGER.error('No input specified. use -i flag')
        sys.exit(1)
    elif os.path.exists(descriptor):
        if os.path.isfile(descriptor):
            # Single image file
            if ImageInputData.is_valid(descriptor):
                LOGGER.debug('Image input data detected for {}'.format(descriptor))
                return ImageInputData(descriptor, **kwargs)
            # Single video file
            elif VideoInputData.is_valid(descriptor):
                LOGGER.debug('Video input data detected for {}'.format(descriptor))
                return VideoInputData(descriptor, **kwargs)
            # Studio json containing images location
            elif not kwargs['predict_from_json'] and ImagesLocationStudioJsonInputData.is_valid(descriptor):
                LOGGER.debug('Image location studio json input data detected for {}'.format(descriptor))
                return ImagesLocationStudioJsonInputData(descriptor, **kwargs)
            # Studio or vulcan json containing images location and predictions
            elif kwargs['predict_from_json'] and ImagesPredictionJsonInputData.is_valid(descriptor):
                LOGGER.debug('Image prediction json input data detected for {}'.format(descriptor))
                return ImagesPredictionJsonInputData(descriptor, **kwargs)
            else:
                LOGGER.error('Unsupported input file type')
                sys.exit(1)
        # Input directory containing images, videos, or json
        elif os.path.isdir(descriptor):
            LOGGER.debug('Directory input data detected for {}'.format(descriptor))
            return DirectoryInputData(descriptor, **kwargs)
        else:
            LOGGER.error('Unknown input path')
            sys.exit(1)
    # Device indicated by digit number such as a webcam
    elif descriptor.isdigit():
        LOGGER.debug('Device input data detected for {}'.format(descriptor))
        return DeviceInputData(descriptor, **kwargs)
    # Video stream such as RTSP
    elif StreamInputData.is_valid(descriptor):
        LOGGER.debug('Stream input data detected for {}'.format(descriptor))
        return StreamInputData(descriptor, **kwargs)
    else:
        LOGGER.error('Unknown input')
        sys.exit(1)


class InputThread(Thread):
    def __init__(self, exit_event, input_queue, output_queue, inputs):
        super(InputThread, self).__init__(exit_event, input_queue, output_queue)
        self.inputs = inputs
        self.frame_number = 0  # Used to keep input order, notably for video reconstruction

    def process_msg(self, _unused):
        try:
            frame = next(self.inputs)
        except StopIteration:
            self.stop()
            return

        if self.inputs.is_infinite():
            # Discard all previous inputs
            clear_queue(self.output_queue)

        frame.frame_number = self.frame_number
        # TODO: for a stream put should not be blocking
        return frame

    def put_to_output(self, msg):
        super(InputThread, self).put_to_output(msg)
        self.frame_number += 1


def input_loop(kwargs, postprocessing=None):
    # Adds smartness to fps handling
    #   1) If both input_fps and output_fps are set, then use them as is.
    #   2) If only one of the two is used, make both equal
    #   3) If none is set:
    #       * If the input is not a video, do nothing and use the default DEFAULT_FPS output value
    #       * If the input is a video, use the input fps as the output fps
    if kwargs['input_fps'] and kwargs['output_fps']:
        pass
    elif kwargs['input_fps']:
        kwargs['output_fps'] = kwargs['input_fps']
        LOGGER.info('Input fps of {} specified, but no output fps specified. Using same value for both.'.format(kwargs['input_fps']))
    elif kwargs['output_fps']:
        kwargs['input_fps'] = kwargs['output_fps']
        LOGGER.info('Output fps of {} specified, but no input fps specified. Using same value for both.'.format(kwargs['output_fps']))

    # Compute inputs now to access actual input fps if it's a video
    inputs = iter(get_input(kwargs.get('input', 0), kwargs))

    # Deal with last case for fps
    if not(kwargs['input_fps']) and not(kwargs['output_fps']) and isinstance(inputs, VideoInputData):
        kwargs['input_fps'] = inputs.get_fps()
        kwargs['output_fps'] = kwargs['input_fps']
        LOGGER.info('Input fps of {} automatically detected, but no output fps specified. Using same value for both.'.format(kwargs['input_fps']))

    # Initialize progress bar
    max_value = int(inputs.get_frame_count()) if inputs.get_frame_count() >= 0 else None
    tqdmout = TqdmToLogger(LOGGER, level=LOGGER.getEffectiveLevel())
    pbar = tqdm(total=max_value, file=tqdmout, desc='Input processing', smoothing=0)

    # For realtime, queue should be LIFO
    # TODO: might need to rethink the whole pipeling for infinite streams
    # IMPORTANT: maxsize is important, it allows to regulate the pipeline and avoid to pushes too many requests to rabbitmq when we are already waiting for many results
    queue_cls = LifoQueue if inputs.is_infinite() else Queue
    queues = [queue_cls(maxsize=QUEUE_MAX_SIZE) for i in range(4)]

    # Initialize workflow for mutual use between send inference pool and result inference pool
    try:
        workflow = get_workflow(kwargs)
    except DeepoCLICredentialsError as e:
        LOGGER.error(str(e))
        sys.exit(1)
    exit_event = threading.Event()

    current_frames = CurrentFrames()

    pools = [
        Pool(1, InputThread, thread_args=(exit_event, None, queues[0], inputs)),
        # Encode image into jpeg
        Pool(1, PrepareInferenceThread, thread_args=(exit_event, queues[0], queues[1], current_frames)),
        # Send inference
        Pool(5, SendInferenceGreenlet, thread_args=(exit_event, queues[1], queues[2], current_frames, workflow)),
        # Gather inference predictions from the worker(s)
        Pool(1, ResultInferenceGreenlet, thread_args=(exit_event, queues[2], queues[3], current_frames, workflow), thread_kwargs=kwargs),
        # Output predictions
        Pool(1, OutputThread, thread_args=(exit_event, queues[3], None, current_frames, pbar.update, postprocessing), thread_kwargs=kwargs)
    ]

    loop = MainLoop(pools, queues, pbar, lambda: workflow.close())
    stop_asked = loop.run_forever()

    # If the process encountered an error, the exit code is 1.
    # If the process is interrupted using SIGINT (ctrl + C) or SIGTERM, the queues are emptied and processed by the
    # threads, and the exit code is 0.
    # If SIGINT or SIGTERM is sent again during this shutdown phase, the threads are killed, and the exit code is 2.
    if exit_event.is_set():
        sys.exit(1)
    elif stop_asked >= 2:
        sys.exit(2)


class InputData(object):
    def __init__(self, descriptor,  **kwargs):
        self._descriptor = descriptor
        self._args = kwargs
        self._name, _ = os.path.splitext(os.path.basename(str(descriptor)))
        self._filename = str(descriptor)
        recognition_id = kwargs.get('recognition_id', '')
        self._reco = '' if recognition_id is None else recognition_id

    def __iter__(self):
        raise NotImplementedError()

    def __next__(self):
        raise NotImplementedError()

    def next(self):
        return self.__next__()  # for python 2

    def get_fps(self):
        raise NotImplementedError()

    def get_frame_count(self):
        raise NotImplementedError()

    def is_infinite(self):
        raise NotImplementedError()


class ImageInputData(InputData):
    @classmethod
    def is_valid(cls, descriptor):
        _, ext = os.path.splitext(descriptor)
        return os.path.exists(descriptor) and ext in SUPPORTED_IMAGE_INPUT_FORMAT

    def __init__(self, descriptor, **kwargs):
        super(ImageInputData, self).__init__(descriptor, **kwargs)
        self._name = '%s_%s' % (self._name, self._reco)

    def __iter__(self):
        self._iterator = iter([Frame(self._name, self._filename, cv2.imread(self._descriptor, 1))])
        return self

    def __next__(self):
        return next(self._iterator)

    def get_fps(self):
        return 0

    def get_frame_count(self):
        return 1

    def is_infinite(self):
        return False


class VideoInputData(InputData):
    @classmethod
    def is_valid(cls, descriptor):
        _, ext = os.path.splitext(descriptor)
        return os.path.exists(descriptor) and ext in SUPPORTED_VIDEO_INPUT_FORMAT

    def __init__(self, descriptor, **kwargs):
        super(VideoInputData, self).__init__(descriptor, **kwargs)
        self._i = 0
        self._name = '%s_%s_%s' % (self._name, '%05d', self._reco)
        self._cap = None
        self._open_video()
        self._kwargs_fps = kwargs['input_fps']
        self._skip_frame = kwargs['skip_frame']
        self._extract_fps = None
        self._fps = self.get_fps()

    def _open_video(self, raise_exc=True):
        if self._cap is not None:
            self._cap.release()
        self._cap = cv2.VideoCapture(self._descriptor)

        if not self._cap.isOpened():
            self._cap = None
            if raise_exc:
                LOGGER.error("Could not open video {}".format(self._descriptor))
                sys.exit(1)
            return False
        return True

    def __iter__(self):
        self._open_video()
        self._i = 0
        self._frames_to_skip = 0
        self._should_skip_fps = self._video_fps
        return self

    def _stop_video(self, raise_exc=True):
        self._cap.release()
        if raise_exc:
            raise StopIteration()

    def _grab_next(self):
        grabbed = self._cap.grab()
        if not grabbed:
            self._stop_video()

    def _decode_next(self):
        decoded, frame = self._cap.retrieve()
        if not decoded:
            self._stop_video()
        else:
            self._i += 1
            return Frame(self._name % self._i, self._filename, frame, self._i)

    def _read_next(self):
        read, frame = self._cap.read()
        if read:
            self._i += 1
            return Frame(self._name % self._i, self._filename, frame, self._i)
        else:
            self._stop_video()

    def __next__(self):
        # make sure we don't enter infinite loop
        assert self._frames_to_skip >= 0
        assert self._extract_fps >= 0

        while True:
            # first, check if the frame should be skipped because of extract fps
            if self._extract_fps > 0:
                if self._should_skip_fps < self._video_fps:
                    self._grab_next()
                    self._should_skip_fps += self._extract_fps
                    continue
                else:
                    self._should_skip_fps += self._extract_fps - self._video_fps

            # then, check if the frame should be skipped because of skipped frame
            if self._frames_to_skip:
                self._grab_next()
                self._frames_to_skip -= 1
                continue
            else:
                self._frames_to_skip = self._skip_frame

            return self._read_next()

    def get_fps(self):
        # There are three different type of fps:
        #   _video_fps: original video fps
        #   _kwarg_fps: fps specified by the user through the CLI if any
        #   _extract_fps: fps used for frame extraction
        assert(self._cap is not None)
        # Retrieve the original video fps if available
        try:
            self._video_fps = self._cap.get(cv2.CAP_PROP_FPS)
        except Exception:
            LOGGER.error('Could not read fps for video {}, please specify it with --input_fps option.'.format(self._descriptor))
            sys.exit(1)
        if self._video_fps == 0:
            LOGGER.error('Null fps detected for video {}, please specify it with --input_fps option.'.format(self._descriptor))
            sys.exit(1)

        # Compute fps for frame extraction so that we don't analyze useless frame that will be discarded later
        if self._extract_fps == None:  # ensures we compute it only once
            if not self._kwargs_fps:
                self._extract_fps = self._video_fps
                LOGGER.debug('No --input_fps specified, using raw video fps of {}'.format(self._video_fps))
            elif self._kwargs_fps < self._video_fps:
                self._extract_fps = self._kwargs_fps
                LOGGER.debug('Using user-specified --input_fps of {} instead of raw video fps of {}'.format(self._kwargs_fps, self._video_fps))
            else:
                self._extract_fps = self._video_fps
                LOGGER.debug('User-specified --input_fps of {} specified but using maximum raw video fps of {}'.format(self._kwargs_fps, self._video_fps))

        return self._extract_fps

    def get_frame_count(self):
        assert self._video_fps > 0

        fps_ratio = self._extract_fps / self._video_fps
        skip_ratio = 1. / (1 + self._skip_frame)
        try:
            return int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT) * fps_ratio * skip_ratio)
        except:
            LOGGER.warning('Cannot compute the total frame count')
            return 0

    def is_infinite(self):
        return False


class DirectoryInputData(InputData):
    @classmethod
    def is_valid(cls, descriptor):
        return (os.path.exists(descriptor) and os.path.isdir(descriptor))

    def __init__(self, descriptor, **kwargs):
        super(DirectoryInputData, self).__init__(descriptor, **kwargs)
        self._current = None
        self._files = []
        self._inputs = []
        self._i = 0
        self._recursive = self._args['recursive']

        if self.is_valid(descriptor):
            _paths = [os.path.join(descriptor, name) for name in os.listdir(descriptor)]
            self._inputs = []
            for path in sorted(_paths):
                if ImageInputData.is_valid(path):
                    LOGGER.debug('Image input data detected for {}'.format(path))
                    self._inputs.append(ImageInputData(path, **kwargs))
                elif VideoInputData.is_valid(path):
                    LOGGER.debug('Video input data detected for {}'.format(path))
                    self._inputs.append(VideoInputData(path, **kwargs))
                elif not kwargs['predict_from_json'] and ImagesLocationStudioJsonInputData.is_valid(path):
                    LOGGER.debug('Image location studio json input data detected for {}'.format(path))
                    self._inputs.append(ImagesLocationStudioJsonInputData(path, **kwargs))
                elif kwargs['predict_from_json'] and ImagesPredictionJsonInputData.is_valid(path):
                    LOGGER.debug('Image prediction json input data detected for {}'.format(path))
                    self._inputs.append(ImagesPredictionJsonInputData(path, **kwargs))
                elif self._recursive and self.is_valid(path):
                    LOGGER.debug('Directory input data detected for {}'.format(path))
                    self._inputs.append(DirectoryInputData(path, **kwargs))

    def _gen(self):
        for source in self._inputs:
            for frame in source:
                self._i += 1
                yield frame

    def __iter__(self):
        self.gen = self._gen()
        self._i = 0
        return self

    def __next__(self):
        return next(self.gen)

    def get_frame_count(self):
        return sum([_input.get_frame_count() for _input in self._inputs])

    def get_fps(self):
        return 1

    def is_infinite(self):
        return False


class StreamInputData(VideoInputData):
    @classmethod
    def is_valid(cls, descriptor):
        return '://' in descriptor and descriptor.split('://')[0] in SUPPORTED_PROTOCOLS_INPUT

    def __init__(self, descriptor, **kwargs):
        super(StreamInputData, self).__init__(descriptor, **kwargs)
        self._name = 'stream_%s_%s' % ('%05d', self._reco)

    def get_frame_count(self):
        return -1

    def is_infinite(self):
        return True


class DeviceInputData(VideoInputData):

    @classmethod
    def is_valid(cls, descriptor):
        return descriptor.isdigit()

    def __init__(self, descriptor, **kwargs):
        super(DeviceInputData, self).__init__(int(descriptor), **kwargs)
        self._name = 'device%s_%s_%s' % (descriptor, '%05d', self._reco)

    def get_frame_count(self):
        return -1

    def is_infinite(self):
        return True


class ImagesPredictionJsonInputData(InputData):
    @classmethod
    def is_valid(cls, descriptor):
        # Check that the file exists
        if not os.path.exists(descriptor):
            return False

        # Check that file is a json
        if not os.path.splitext(descriptor)[1].lower() == '.json':
            return False

        # Check if json is a dictionnary
        try:
            with open(descriptor) as json_file:
                json_data = json.load(json_file)
        except:
            LOGGER.debug('File {} is not a valid json'.format(descriptor))
            return False

        # If a Vulcan json, transform it to Studio
        if 'outputs' in json_data[0]:
            logging.debug('Vulcan json detected for {}'.format(descriptor))
            try:
                json_data = transform_json_from_vulcan_to_studio(json_data)
            except:
                LOGGER.error('Could not transform Vulcan json type to Studio type for {}'.format(descriptor))
                sys.exit(1)
        elif 'images' in json_data:
            logging.debug('Studio json detected for {}'.format(descriptor))
        else:
            LOGGER.error('Could not detect json type for {}'.format(descriptor))
            sys.exit(1)

        exit()

        # Check that the json follows the minimum Studio format
        studio_format_error = 'File {} is not a valid Studio json'.format(descriptor)
        if 'images' not in json_data:
            LOGGER.debug(studio_format_error)
            return False
        elif not isinstance(json_data['images'], list):
            LOGGER.debug(studio_format_error)
            return False
        else:
            for img in json_data['images']:
                if not isinstance(img, dict):
                    LOGGER.debug(studio_format_error)
                    return False
                elif 'location' not in img:
                    LOGGER.debug(studio_format_error)
                    return False
                elif not ImageInputData.is_valid(img['location']):
                    LOGGER.debug('File {} is not valid'.format(img['location']))
                    return False

        return True


class ImagesLocationStudioJsonInputData(InputData):

    @classmethod
    def is_valid(cls, descriptor):
        # Check that the file exists
        if not os.path.exists(descriptor):
            return False

        # Check that file is a json
        if not os.path.splitext(descriptor)[1].lower() == '.json':
            return False

        # Check if json is a dictionnary
        try:
            with open(descriptor) as json_file:
                json_data = json.load(json_file)
        except:
            LOGGER.debug('File {} is not a valid json'.format(descriptor))
            return False

        # Check that the json follows the minimum Studio format
        studio_format_error = 'File {} is not a valid Studio json'.format(descriptor)
        if 'images' not in json_data:
            LOGGER.debug(studio_format_error)
            return False
        elif not isinstance(json_data['images'], list):
            LOGGER.debug(studio_format_error)
            return False
        else:
            for img in json_data['images']:
                if not isinstance(img, dict):
                    LOGGER.debug(studio_format_error)
                    return False
                elif 'location' not in img:
                    LOGGER.debug(studio_format_error)
                    return False
                elif not ImageInputData.is_valid(img['location']):
                    LOGGER.debug('File {} is not valid'.format(img['location']))
                    return False

        return True

    def __init__(self, descriptor, **kwargs):
        super(ImagesLocationStudioJsonInputData, self).__init__(descriptor, **kwargs)
        self._current = None
        self._files = []
        self._inputs = []
        self._i = 0

        if self.is_valid(descriptor):
            with open(descriptor) as json_file:
                json_data = json.load(json_file)
                _paths = [img['location'] for img in json_data['images']]
                _files = [
                    ImageInputData(path, **kwargs) if ImageInputData.is_valid(path) else
                    VideoInputData(path, **kwargs) if VideoInputData.is_valid(path) else
                    None for path in _paths if os.path.isfile(path)]
                self._inputs = [_input for _input in _files if _input is not None]

    def _gen(self):
        for source in self._inputs:
            for frame in source:
                self._i += 1
                yield frame

    def __iter__(self):
        self.gen = self._gen()
        self._i = 0
        return self

    def __next__(self):
        return next(self.gen)

    def get_frame_count(self):
        return sum([_input.get_frame_count() for _input in self._inputs])

    def get_fps(self):
        return 1

    def is_infinite(self):
        return False
