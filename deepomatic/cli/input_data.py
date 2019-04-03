import os
import cv2
import json
import logging
from .cmds.infer import ResultInferenceThread, SendInferenceThread
from tqdm import tqdm
from .common import TqdmToLogger
from .workflow import get_workflow
from .output_data import OutputThread
try:
    from Queue import Queue, LifoQueue, Empty
except ImportError:
    from queue import Queue, LifoQueue, Empty


QUEUE_MAX_SIZE = 50


class Frame(object):
    def __init__(self, name, filename, image, video_frame_index=None):
        self.name = name
        self.filename = filename
        self.image = image  # an opencv loaded image
        self.video_frame_index = video_frame_index
        self.frame_number = None  # frame_number since deepocli started
        self.predictions = None
        self.output_image = None  # frame to output (modified version of the frame)
        self.inference_async_result = None


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


def input_loop(kwargs, postprocessing=None):
    inputs = get_input(kwargs.get('input', 0), kwargs)

    # Initialize progress bar
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger()
    max_value = int(inputs.get_frame_count()) if inputs.get_frame_count() >= 0 else None
    tqdmout = TqdmToLogger(logger, level=logging.INFO)
    pbar = tqdm(total=max_value, file=tqdmout, desc='Input processing', smoothing=0)

    # For realtime, queue should be LIFO
    # The data exchanged in the different queues is of the following format:
    #   - input: data = (frame_number, frame_name, frame_filename, frame_payload)
    #   - worker: data = (frame_number, frame_name, frame_filename, frame_payload, frame_correlation_id)
    #   - output: data = (frame_number, frame_name, frame_modified, frame_prediction)
    # With:
    #   - frame_number: the frame number is the input sequence
    #   - frame_name: the new name of the frame
    #   - frame_filename: the original filename from which the frame was extracted
    #   - frame_payload: the original pixels of the frame
    #   - frame_correlation_id: the worker-nn correlation id of the frame
    #   - frame_modified: the modifier frame, for instance the blurred frame
    #   - frame_prediction: the actual prediction corresponding to the frame
    # TODO: might need to rethink the whole pipeling for infinite streams
    input_queue = LifoQueue(maxsize=QUEUE_MAX_SIZE) if inputs.is_infinite() else Queue()
    worker_queue = LifoQueue(maxsize=QUEUE_MAX_SIZE) if inputs.is_infinite() else Queue()
    output_queue = LifoQueue(maxsize=QUEUE_MAX_SIZE) if inputs.is_infinite() else Queue()

    # Initialize workflow for mutual use between input and worker threads:
    #   - input thread uses it to send frames
    #   - worker thread uses it to retrieve predictions
    # Note: the workflow is closed by the worker thread
    workflow = get_workflow(kwargs)

    # Define threads
    #   - input: prepares input and send it to worker
    #   - worker: retrieves prediction from worker
    #   - output: transforms predictions into outputs
    send_inference_thread = SendInferenceThread(input_queue, worker_queue, workflow, postprocessing=postprocessing, **kwargs)
    result_inference_thread = ResultInferenceThread(worker_queue, output_queue, workflow, **kwargs)
    output_thread = OutputThread(output_queue, on_progress=lambda i: pbar.update(1), **kwargs)

    stop_asked = 0
    # Start threads
    send_inference_thread.start()
    result_inference_thread.start()
    output_thread.start()

    while True:
        try:
            if not stop_asked:
                frame_number = 0  # Used to keep input order, notably for video reconstruction
                for frame in inputs:
                    frame.frame_number = frame_number
                    if inputs.is_infinite():
                        # Discard all previous inputs
                        while not input_queue.empty():
                            try:
                                input_queue.get(block=False)
                                input_queue.task_done()
                            except Empty:
                                break

                    # while input_queue.qsize() > QUEUE_MAX_SIZE or worker_queue.qsize() > QUEUE_MAX_SIZE:
                    #     time.sleep(1)

                    input_queue.put(frame)
                    frame_number += 1

            send_inference_thread.stop_when_no_input()
            result_inference_thread.stop_when_no_input()
            output_thread.stop_when_no_input()
            break
        except (KeyboardInterrupt, SystemExit):
            stop_asked += 1
            if stop_asked >= 2:
                send_inference_thread.stop()
                result_inference_thread.stop()
                output_thread.stop()
                logging.info("Hard stop")
                break
            else:
                logging.info('Stop asked, waiting for threads to process queued messages.')

    pbar.close()


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
        return iter([Frame(self._name, self._filename, cv2.imread(self._descriptor, 1))])

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
        self._cap = cv2.VideoCapture(self._descriptor)
        if self._cap is not None:
            raw_fps = self._cap.get(cv2.CAP_PROP_FPS)
            desired_fps = min(kwargs['fps'], raw_fps) if kwargs['fps'] else raw_fps
            # TODO: find a better name for fps, as it is actually a ratio indicating which frames number to process in the video (other are ignored)
            logging.info('Detected raw video fps of {}, using fps of {}'.format(raw_fps, desired_fps))
            total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT) * desired_fps / raw_fps)
            self._fps = desired_fps
            self._adjusted_frames = [round(frame * raw_fps / desired_fps) for frame in range(0, total_frames)]
            self._total_frames = len(self._adjusted_frames)
        else:
            self._fps = None
            self._total_frames = None
            self._adjusted_frames = None

    def __iter__(self):
        if self._cap is not None:
            self._cap.release()
        self._cap = cv2.VideoCapture(self._descriptor)
        self._i = 0
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
            for path in _paths:
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
