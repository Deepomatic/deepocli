import os
import cv2
import logging

from .common import (SUPPORTED_IMAGE_INPUT_FORMAT, SUPPORTED_PROTOCOLS_INPUT,
                     SUPPORTED_VIDEO_INPUT_FORMAT, clear_queue)
from .exceptions import DeepoFPSError, DeepoInputError, DeepoVideoOpenError
from .frame import Frame
from .thread_base import Thread


LOGGER = logging.getLogger(__name__)


def get_input(descriptor, kwargs):
    if descriptor is None:
        raise DeepoInputError('No input specified. use -i flag')
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
            else:
                raise DeepoInputError('Unsupported input file type')
        # Input directory containing images, videos, or json
        elif os.path.isdir(descriptor):
            LOGGER.debug('Directory input data detected for {}'.format(descriptor))
            return DirectoryInputData(descriptor, **kwargs)
        else:
            raise DeepoInputError('Unknown input path')
    # Device indicated by digit number such as a webcam
    elif descriptor.isdigit():
        LOGGER.debug('Device input data detected for {}'.format(descriptor))
        return DeviceInputData(descriptor, **kwargs)
    # Video stream such as RTSP
    elif StreamInputData.is_valid(descriptor):
        LOGGER.debug('Stream input data detected for {}'.format(descriptor))
        return StreamInputData(descriptor, **kwargs)
    else:
        raise DeepoInputError('Unknown input')


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


class InputData(object):
    def __init__(self, descriptor, **kwargs):
        self._args = kwargs
        self._descriptor = descriptor
        self._filename = str(descriptor)
        self._name = os.path.basename(os.path.normpath(self._filename))
        base, ext = os.path.splitext(self._name)
        if ext:
            self._name = '{}_{}'.format(base, ext.lstrip('.'))
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
        return os.path.exists(descriptor) and ext.lower() in SUPPORTED_IMAGE_INPUT_FORMAT

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
        return os.path.exists(descriptor) and ext.lower() in SUPPORTED_VIDEO_INPUT_FORMAT

    def __init__(self, descriptor, **kwargs):
        super(VideoInputData, self).__init__(descriptor, **kwargs)
        self._absolute_video_frame_index = 0
        self._decoded_video_frame_index = 0
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
                raise DeepoVideoOpenError("Could not open video {}".format(self._descriptor))
            return False
        return True

    def __iter__(self):
        self._open_video()
        self._absolute_video_frame_index = 0
        self._decoded_video_frame_index = 0
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
        else:
            self._absolute_video_frame_index += 1

    def _decode_next(self):
        decoded, frame = self._cap.retrieve()
        if not decoded:
            self._stop_video()
        else:
            self._decoded_video_frame_index += 1
            return Frame(self._name % self._absolute_video_frame_index,
                         self._filename, frame,
                         self._decoded_video_frame_index,
                         self._absolute_video_frame_index)

    def _read_next(self):
        read, frame = self._cap.read()
        if read:
            self._absolute_video_frame_index += 1
            self._decoded_video_frame_index += 1
            return Frame(self._name % self._absolute_video_frame_index,
                         self._filename, frame,
                         self._decoded_video_frame_index,
                         self._absolute_video_frame_index)
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
            raise DeepoFPSError('Could not read fps for video {}, please specify it with --input_fps option.'.format(self._descriptor))
        if self._video_fps == 0:
            raise DeepoFPSError('Null fps detected for video {}, please specify it with --input_fps option.'.format(self._descriptor))

        # Compute fps for frame extraction so that we don't analyze useless frame that will be discarded later
        if not self._kwargs_fps:
            self._extract_fps = self._video_fps
            LOGGER.debug('No --input_fps specified, using raw video fps of {}'.format(self._video_fps))
        elif self._kwargs_fps < self._video_fps:
            self._extract_fps = self._kwargs_fps
            LOGGER.debug('Using user-specified --input_fps of {} instead of raw video fps of {}'.format(self._kwargs_fps, self._video_fps))
        else:
            self._extract_fps = self._video_fps
            LOGGER.debug('User-specified --input_fps of {} specified'
                         ' but using maximum raw video fps of {}'.format(self._kwargs_fps, self._video_fps))

        return self._extract_fps

    def get_frame_count(self):
        assert self._video_fps > 0

        fps_ratio = self._extract_fps / self._video_fps
        skip_ratio = 1. / (1 + self._skip_frame)
        try:
            return int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT) * fps_ratio * skip_ratio)
        except Exception:
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
                elif self._recursive and self.is_valid(path):
                    LOGGER.debug('Directory input data detected for {}'.format(path))
                    self._inputs.append(DirectoryInputData(path, **kwargs))

    def _gen(self):
        for source in self._inputs:
            for frame in source:
                yield frame

    def __iter__(self):
        self.gen = self._gen()
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
        return '://' in descriptor and descriptor.split('://')[0].lower() in SUPPORTED_PROTOCOLS_INPUT

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
