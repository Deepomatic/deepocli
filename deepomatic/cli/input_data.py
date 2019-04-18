import os
import cv2
import sys
import json
import logging
import threading
import gevent
from .thread_base import Pool, Thread, Queue, LifoQueue, MainLoop, QUEUE_MAX_SIZE
from .cmds.infer import SendInferenceGreenlet, ResultInferenceGreenlet, PrepareInferenceThread
from tqdm import tqdm
from .common import TqdmToLogger
from .workflow import get_workflow
from .output_data import OutputThread


LOGGER = logging.getLogger(__name__)


class Frame(object):
    def __init__(self, name, filename, image, video_frame_index=None):
        # The Frame object is used as a data exchanged in the different queues
        self.name = name  # name of the frame
        self.filename = filename  # the original filename from which the frame was extracted
        self.image = image  # an opencv loaded image (numpy array)
        self.video_frame_index = video_frame_index  # index of the frame in the video sequence
        self.frame_number = None  # frame_number since deepocli started (set by input_loop)
        self.inference_async_result = None  # an inference request object that will allow us to retrieve the predictions when ready
        self.predictions = None  # predictions result dict
        self.output_image = None  # frame to output (modified version of the image, check infer postprocessings draw/blur)
        self.buf_bytes = None

    def __str__(self):
        return '<Frame name={} filename={} frame_number={} video_frame_index={}>'.format(
            self.name, self.filename, self.frame_number, self.video_frame_index)


def get_input(descriptor, kwargs):
    if descriptor is None:
        raise NameError('No input specified. use -i flag')
    elif os.path.exists(descriptor):
        if os.path.isfile(descriptor):
            if ImageInputData.is_valid(descriptor):
                return ImageInputData(descriptor, **kwargs)
            elif VideoInputData.is_valid(descriptor):
                return VideoInputData(descriptor, **kwargs)
            elif JsonInputData.is_valid(descriptor):
                return JsonInputData(descriptor, **kwargs)
            else:
                raise NameError('Unsupported input file type')
        elif os.path.isdir(descriptor):
            return DirectoryInputData(descriptor, **kwargs)
        else:
            raise NameError('Unknown input path')
    elif descriptor.isdigit():
        return DeviceInputData(descriptor, **kwargs)
    elif StreamInputData.is_valid(descriptor):
        return StreamInputData(descriptor, **kwargs)
    else:
        raise NameError('Unknown input')


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

        frame.frame_number = self.frame_number
        if self.inputs.is_infinite():
            # Discard all previous inputs
            with self.output_queue.mutex:
                self.output_queue.clear()

        # TODO: for a stream put should not be blocking
        return frame

    def put_to_output(self, msg):
        super(InputThread, self).put_to_output(msg)
        self.frame_number += 1


def input_loop(kwargs, postprocessing=None):
    inputs = iter(get_input(kwargs.get('input', 0), kwargs))

    # Initialize progress bar
    max_value = int(inputs.get_frame_count()) if inputs.get_frame_count() >= 0 else None
    tqdmout = TqdmToLogger(LOGGER, level=logging.INFO)
    pbar = tqdm(total=max_value, file=tqdmout, desc='Input processing', smoothing=0)

    # For realtime, queue should be LIFO
    # TODO: might need to rethink the whole pipeling for infinite streams
    # IMPORTANT: maxsize is important, it allows to regulate the pipeline and avoid to pushes too many requests to rabbitmq when we are already waiting for many results
    queue_cls = LifoQueue if inputs.is_infinite() else Queue
    queues = [queue_cls(maxsize=QUEUE_MAX_SIZE) for i in range(4)]

    # Initialize workflow for mutual use between send inference pool and result inference pool
    workflow = get_workflow(kwargs)
    exit_event = threading.Event()

    pools = [
        Pool(1, InputThread, thread_args=(exit_event, None, queues[0], inputs)),
        # Encode image into jpeg
        Pool(1, PrepareInferenceThread, thread_args=(exit_event, queues[0], queues[1])),
        # Send inference
        Pool(5, SendInferenceGreenlet, thread_args=(exit_event, queues[1], queues[2], workflow)),
        # Gather inference predictions from the worker(s)
        Pool(1, ResultInferenceGreenlet, thread_args=(exit_event, queues[2], queues[3], workflow), thread_kwargs=kwargs),
        # Output predictions
        Pool(1, OutputThread, thread_args=(exit_event, queues[3], None, pbar.update, postprocessing), thread_kwargs=kwargs)
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
    supported_formats = ['.bmp', '.jpeg', '.jpg', '.jpe', '.png']

    @classmethod
    def is_valid(cls, descriptor):
        _, ext = os.path.splitext(descriptor)
        return os.path.exists(descriptor) and ext in cls.supported_formats

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
    supported_formats = ['.avi', '.mp4', '.webm', '.mjpg']

    @classmethod
    def is_valid(cls, descriptor):
        _, ext = os.path.splitext(descriptor)
        return os.path.exists(descriptor) and ext in cls.supported_formats

    def __init__(self, descriptor, **kwargs):
        super(VideoInputData, self).__init__(descriptor, **kwargs)
        self._i = 0
        self._name = '%s_%s_%s' % (self._name, '%05d', self._reco)
        self._fps_opt = kwargs['fps']
        self._open_video(raise_exc=False)

    def _open_video(self, raise_exc=True):
        self._cap = cv2.VideoCapture(self._descriptor)
        if not self._cap.isOpened():
            self._cap = None
            if raise_exc:
                raise Exception("Could not open video {}".format(self._descriptor))
            return False

        raw_fps = self._cap.get(cv2.CAP_PROP_FPS)
        desired_fps = min(self._fps_opt, raw_fps) if self._fps_opt else raw_fps
        # TODO: find a better name for fps, as it is actually a ratio indicating which frames number to process in the video (other are ignored)
        LOGGER.info('Detected raw video fps of {}, using fps of {}'.format(raw_fps, desired_fps))
        # Compute the total number of frames and ensure we always have at least one frame
        total_frames = max(1, int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT) * desired_fps / raw_fps))
        self._fps = desired_fps
        self._adjusted_frames = [round(frame * raw_fps / desired_fps) for frame in range(0, total_frames)]
        self._total_frames = len(self._adjusted_frames)
        self._i = 0
        return True

    def __iter__(self):
        if self._cap is not None:
            self._cap.release()
        self._open_video()
        return self

    def __next__(self):
        if self._cap.isOpened():
            while self._i not in self._adjusted_frames:
                self._i += 1
                _, frame = self._cap.read()
                if frame is None:
                    self._cap.release()
                    raise StopIteration
            self._i += 1
            _, frame = self._cap.read()
            return Frame(self._name % self._i, self._filename, frame, self._i)
        self._cap.release()
        raise StopIteration

    def get_fps(self):
        return self._fps

    def get_frame_count(self):
        return self._total_frames

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
                    self._inputs.append(ImageInputData(path, **kwargs))
                elif VideoInputData.is_valid(path):
                    self._inputs.append(VideoInputData(path, **kwargs))
                elif self._recursive and self.is_valid(path):
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
    supported_protocols = ['rtsp', 'http', 'https']

    @classmethod
    def is_valid(cls, descriptor):
        return '://' in descriptor and descriptor.split('://')[0] in cls.supported_protocols

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


class JsonInputData(InputData):

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
        except Exception:
            raise NameError('File {} is not a valid json'.format(descriptor))

        # Check that the json follows the minimum Studio format
        studio_format_error = 'File {} is not a valid Studio json'.format(descriptor)
        if 'images' not in json_data:
            raise NameError(studio_format_error)
        elif not isinstance(json_data['images'], list):
            raise NameError(studio_format_error)
        else:
            for img in json_data['images']:
                if not isinstance(img, dict):
                    raise NameError(studio_format_error)
                elif 'location' not in img:
                    raise NameError(studio_format_error)
                elif not ImageInputData.is_valid(img['location']):
                    raise NameError('File {} is not valid'.format(img['location']))
        return True

    def __init__(self, descriptor, **kwargs):
        super(JsonInputData, self).__init__(descriptor, **kwargs)
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
