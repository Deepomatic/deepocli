import os
import sys
import json
import imutils
import logging
import cv2
import time
import threading
from tqdm import tqdm
from deepomatic.cli.workflow import get_workflow

try:
    from Queue import Queue, LifoQueue, Empty
except ImportError:
    from queue import Queue, LifoQueue, Empty

QUEUE_MAX_SIZE = 50
END_OF_STREAM_MSG = "__END_OF_STREAM__"
TERMINATION_MSG = "__TERMINATION_MSG__"

def print_log(log):
    """Uses tqdm helper function to ensure progressbar stays at the bottom."""
    tqdm.write(log)

def save_json_to_file(json_data, json_path):
    try:
        with open('%s.json' % json_path, 'w') as file:
            print_log('Writing %s.json' % json_path)
            json.dump(json_data, file)
    except:
        logging.error("Could not save file {} in json format.".format(json_path))
        raise

    return

def get_input(descriptor, kwargs):
    if (descriptor is None):
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

def get_output(descriptor, kwargs):
    if descriptor is not None:
        if DirectoryOutputData.is_valid(descriptor):
            return DirectoryOutputData(descriptor, **kwargs)
        elif ImageOutputData.is_valid(descriptor):
            return ImageOutputData(descriptor, **kwargs)
        elif VideoOutputData.is_valid(descriptor):
            return VideoOutputData(descriptor, **kwargs)
        elif JsonOutputData.is_valid(descriptor):
            return JsonOutputData(descriptor, **kwargs)
        elif descriptor == 'stdout':
            return StdOutputData(**kwargs)
        elif descriptor == 'window':
            return DisplayOutputData(**kwargs)
        else:
            raise NameError('Unknown output')
    else:
        return DisplayOutputData(**kwargs)

def input_loop(kwargs, WorkerThread):
    inputs = get_input(kwargs.get('input', 0), kwargs)

    # Initialize progress bar
    max_value = inputs.get_frame_count()
    max_value = int(max_value) if max_value >= 0 else None  # ensure it's int for tqdm display
    pbar = tqdm(total=max_value)

    # For realtime, queue should be LIFO
    input_queue = LifoQueue() if inputs.is_infinite() else Queue()
    worker_queue = LifoQueue() if inputs.is_infinite() else Queue()
    output_queue = LifoQueue() if inputs.is_infinite() else Queue()

    # Initialize workflow for mutual use between input and worker threads:
    #   - input thread uses it to send frames
    #   - worker thread uses it to retrieve predictions
    # Note: the workflow is closed by the worker thread
    workflow = get_workflow(kwargs)
    workflow_lock = threading.Lock()  # Controls access to underlying socket

    # Define threads
    #   - input: prepares input and send it to worker
    #   - worker: retrieves prediction from worker
    #   - output: transforms predictions into outputs
    input_thread = InputThread(input_queue, worker_queue, workflow, workflow_lock, **kwargs)
    worker_thread = WorkerThread(worker_queue, output_queue, workflow, workflow_lock, **kwargs)
    output_thread = OutputThread(output_queue, on_progress=lambda i: pbar.update(1), **kwargs)

    # Start threads
    input_thread.start()
    worker_thread.start()
    output_thread.start()

    try:
        for frame in inputs:
            if inputs.is_infinite():
                # Discard all previous inputs
                while not input_queue.empty():
                    try:
                        input_queue.get(False)
                        input_queue.task_done()
                    except Empty:
                        break

            while input_queue.qsize() > QUEUE_MAX_SIZE or worker_queue.qsize() > QUEUE_MAX_SIZE:
                time.sleep(1)

            input_queue.put(frame)

        # Notify following threads that input stream is over and wait for completion
        input_queue.put(END_OF_STREAM_MSG)
        input_thread.join()
        worker_thread.join()
        output_thread.join()
        pbar.close()

    except KeyboardInterrupt:
        logging.info('Stopping input')
        while not input_queue.empty():
            try:
                input_queue.get(False)
                input_queue.task_done()
            except Empty:
                break
        input_queue.put(TERMINATION_MSG)
        input_thread.join()
        worker_thread.join()
        output_thread.join()

class InputThread(threading.Thread):
    def __init__(self, input_queue, worker_queue, workflow, workflow_lock, **kwargs):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.input_queue = input_queue
        self.worker_queue = worker_queue
        self.workflow = workflow
        self.workflow_lock = workflow_lock
        self.args = kwargs

    def run(self):
        try:
            while 1:
                data = self.input_queue.get()
                if data is END_OF_STREAM_MSG or data is TERMINATION_MSG:
                    self.input_queue.task_done()
                    self.worker_queue.put(data)
                    return

                inference = None
                name, filename, frame = data
                if frame is not None:
                    if self.workflow is not None:
                        with self.workflow_lock:
                            inference = self.workflow.infer(frame)

                self.input_queue.task_done()
                self.worker_queue.put((name, filename, frame, inference))
        except KeyboardInterrupt:
            logging.info('Stopping output')
            while not self.input_queue.empty():
                try:
                    self.input_queue.get(False)
                except Empty:
                    break
                self.input_queue.task_done()
            self.worker_queue.put(TERMINATION_MSG)

class OutputThread(threading.Thread):
    def __init__(self, output_queue, on_progress=None, **kwargs):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.output_queue = output_queue
        self.args = kwargs
        self.on_progress = on_progress

    def run(self):
        i = 0
        with get_output(self.args.get('output', None), self.args) as output_processing:
            try:
                while 1:
                    data = self.output_queue.get()

                    if data is TERMINATION_MSG:
                        self.output_queue.task_done()
                        return
                    elif data is END_OF_STREAM_MSG:
                        self.output_queue.task_done()
                        if not self.output_queue.empty():
                            self.output_queue.put(END_OF_STREAM_MSG)
                            continue
                        else:
                            return
                    else:
                        output_processing(*data)
                        i += 1
                        if self.on_progress:
                            self.on_progress(i)
                        self.output_queue.task_done()
            except KeyboardInterrupt:
                logging.info('Stopping output')
                while not self.output_queue.empty():
                    try:
                        self.output_queue.get(False)
                    except Empty:
                        break
                    self.output_queue.task_done()

class InputData(object):
    def __init__(self, descriptor,  **kwargs):
        self._descriptor = descriptor
        self._args = kwargs
        self._name, _ = os.path.splitext(os.path.basename(str(descriptor)))
        self._filename = str(descriptor)
        recognition_id = kwargs.get('recognition_id', '')
        self._reco = '' if recognition_id is None else recognition_id

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        raise StopIteration

    def get_fps(self):
        raise NotImplementedError()

    def get_frame_name(self):
        raise NotImplementedError()

    def get_frame_index(self):
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
        self._first = None
        self._name = '%s_%s' % (self._name, self._reco)

    def __iter__(self):
        self._first = True
        return self

    def next(self):
        if self._first:
            self._first = False
            return self._name, self._filename, cv2.imread(self._descriptor, 1)
        else:
            raise StopIteration

    def get_fps(self):
        return 0

    def get_frame_name(self):
        return self._name

    def get_frame_index(self):
        return 0 if self._first else 1

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
        self._cap = None
        self._i = 0
        self._name = '%s_%s_%s' % (self._name, '%05d', self._reco)
        self._cap = cv2.VideoCapture(self._descriptor)

    def __iter__(self):
        if self._cap is not None:
            self._cap.release()
        self._cap = cv2.VideoCapture(self._descriptor)
        self._i = 0
        return self

    def next(self):
        if self._cap.isOpened():
            _, frame = self._cap.read()
            if frame is None:
                self._cap.release()
                raise StopIteration
            else:
                self._i += 1
                return self._name % self._i, self._filename, frame
        self._cap.release()
        raise StopIteration

    def get_fps(self):
        if (self._cap is not None):
            return self._cap.get(cv2.CAP_PROP_FPS)
        else:
            return None

    def get_frame_index(self):
        return self._i

    def get_frame_count(self):
        if (self._cap is not None):
            return self._cap.get(cv2.CAP_PROP_FRAME_COUNT)
        else:
            return None

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

    def next(self):
        return next(self.gen)

    def get_frame_index(self):
        return self._i

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
        except:
            raise NameError('File {} is not a valid json'.format(descriptor))

        # Check that the json follows the minimum Studio format
        studio_format_error = 'File {} is not a valid Studio json'.format(descriptor)
        if not 'images' in json_data:
            raise NameError(studio_format_error)
        elif not isinstance(json_data['images'], list):
            raise NameError(studio_format_error)
        else:
            for img in json_data['images']:
                if not isinstance(img, dict):
                    raise NameError(studio_format_error)
                elif not 'location' in img:
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

    def next(self):
        return next(self.gen)

    def get_frame_index(self):
        return self._i

    def get_frame_count(self):
        return sum([_input.get_frame_count() for _input in self._inputs])

    def get_fps(self):
        return 1

    def is_infinite(self):
        return False

class OutputData(object):
    def __init__(self, descriptor, **kwargs):
        self._descriptor = descriptor
        self._args = kwargs
        self._json = kwargs.get('json', False)

    def __enter__(self):
        raise NotImplementedError()

    def __exit__(self, exception_type, exception_value, traceback):
        raise NotImplementedError()

    def __call__(self, name, frame, prediction):
        raise NotImplementedError()


class ImageOutputData(OutputData):
    supported_formats = ['.bmp', '.jpeg', '.jpg', '.jpe', '.png']

    @classmethod
    def is_valid(cls, descriptor):
        _, ext = os.path.splitext(descriptor)
        return ext in cls.supported_formats

    def __init__(self, descriptor, **kwargs):
        super(ImageOutputData, self).__init__(descriptor, **kwargs)
        self._i = 0

    def __enter__(self):
        self._i = 0
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        pass

    def __call__(self, name, frame, prediction):
        path = self._descriptor
        try:
            path = path % self._i
        except TypeError:
            pass
        finally:
            self._i += 1
            if (frame is None):
                logging.warning('No frame to output.')
            else:
                print_log('Writing %s' % path)
                cv2.imwrite(path, frame)
                if self._json:
                    json_path = os.path.splitext(path)[0]
                    save_json_to_file(prediction, json_path)


class VideoOutputData(OutputData):
    supported_formats = ['.avi', '.mp4']

    @classmethod
    def is_valid(cls, descriptor):
        _, ext = os.path.splitext(descriptor)
        return ext in cls.supported_formats

    def __init__(self, descriptor, **kwargs):
        super(VideoOutputData, self).__init__(descriptor, **kwargs)
        ext = os.path.splitext(descriptor)[1]
        if ext == '.avi':
            fourcc = cv2.VideoWriter_fourcc('X', 'V', 'I', 'D')
        elif ext == '.mp4':
            fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
        self._fourcc = fourcc
        self._fps = kwargs.get('output_fps', 25)
        self._writer = None
        self._all_predictions = {'tags': [], 'images': []}

    def __enter__(self):
        if self._writer is not None:
            self._writer.release()
        self._writer = None
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if self._json:
            json_path = os.path.splitext(self._descriptor)[0]
            save_json_to_file(self._all_predictions, json_path)
        if self._writer is not None:
            self._writer.release()
        self._writer = None

    def __call__(self, name, frame, prediction):
        if frame is None:
            logging.warning('No frame to output.')
        else:
            if self._writer is None:
                print_log('Writing %s' % self._descriptor)
                self._writer = cv2.VideoWriter(self._descriptor,
                    self._fourcc,
                    self._fps,
                    (frame.shape[1], frame.shape[0]))
            if self._json:
                self._all_predictions['images'] += prediction['images']
                self._all_predictions['tags'] = list(set(self._all_predictions['tags'] + prediction['tags']))
            self._writer.write(frame)

class DirectoryOutputData(OutputData):
    @classmethod
    def is_valid(cls, descriptor):
        return (os.path.exists(descriptor) and os.path.isdir(descriptor))

    def __init__(self, descriptor, **kwargs):
        super(DirectoryOutputData, self).__init__(descriptor, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        pass

    def __call__(self, name, frame, prediction):
        path = os.path.join(self._descriptor, name)
        if (frame is None):
            if (prediction is None):
                pass
            else:
                with open('%s.json' % path, 'w') as file:
                    print_log('Writing %s.json' % path)
                    json.dump(prediction, file)
        else:
            print_log('Writing %s.jpeg' % path)
            cv2.imwrite('%s.jpeg' % path, frame)
            if self._json:
                save_json_to_file(prediction, path)

class DrawOutputData(OutputData):

    def __init__(self, **kwargs):
        super(DrawOutputData, self).__init__(None, **kwargs)
        self._draw_labels = kwargs.get('draw_labels', False)
        self._draw_scores = kwargs.get('draw_scores', False)

    def __call__(self, name, frame, prediction, font_scale=0.5):
        frame = frame.copy()
        h = frame.shape[0]
        w = frame.shape[1]
        for pred in prediction['images'][0]['annotated_regions']:
            # Build legend
            label = ''
            if self._draw_labels:
                label += ', '.join(pred['tags'])
            if self._draw_labels and self._draw_scores:
                label += ' '
            if self._draw_scores:
                label += str(pred['score'])

            # Check that we have a bounding box
            if 'region' in pred:
                # Retrieve coordinates
                bbox = pred['region']
                xmin = int(bbox['xmin'] * w)
                ymin = int(bbox['ymin'] * h)
                xmax = int(bbox['xmax'] * w)
                ymax = int(bbox['ymax'] * h)

                # Draw bounding box
                color = (255, 0, 0)
                cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), color, 1)
                ret, baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
                cv2.rectangle(frame, (xmin, ymax - ret[1] - baseline), (xmin + ret[0], ymax), (0, 0, 255), -1)
                cv2.putText(frame, label, (xmin, ymax - baseline), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 1)

        return name, frame, prediction

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        pass

class BlurOutputData(OutputData):

    def __init__(self, **kwargs):
        super(BlurOutputData, self).__init__(None, **kwargs)
        self._method = kwargs.get('blur_method', 'pixel')
        self._strength = int(kwargs.get('blur_strength', 10))

    def __call__(self, name, frame, prediction, font_scale=0.5):
        frame = frame.copy()
        h = frame.shape[0]
        w = frame.shape[1]
        for pred in prediction['images'][0]['annotated_regions']:
            # Check that we have a bounding box
            if 'region' in pred:
                # Retrieve coordinates
                bbox = pred['region']
                xmin = int(bbox['xmin'] * w)
                ymin = int(bbox['ymin'] * h)
                xmax = int(bbox['xmax'] * w)
                ymax = int(bbox['ymax'] * h)

                # Draw
                if self._method == 'black':
                    cv2.rectangle(frame,(xmin, ymin),(xmax, ymax),(0,0,0),-1)
                elif self._method == 'gaussian':
                    face = frame[ymin:ymax, xmin:xmax]
                    face = cv2.GaussianBlur(face, (15, 15), self._strength)
                    frame[ymin:ymax, xmin:xmax] = face
                elif self._method == 'pixel':
                    face = frame[ymin:ymax, xmin:xmax]
                    small = cv2.resize(face, (0,0),
                        fx=1./min((xmax - xmin), self._strength),
                        fy=1./min((ymax - ymin), self._strength))
                    face = cv2.resize(small, ((xmax - xmin), (ymax - ymin)), interpolation=cv2.INTER_NEAREST)
                    frame[ymin:ymax, xmin:xmax] = face

        return name, frame, prediction

    def __enter__(self):
        return self
    def __exit__(self, exception_type, exception_value, traceback):
        pass

class StdOutputData(OutputData):
    def __init__(self, **kwargs):
        super(StdOutputData, self).__init__(None, **kwargs)

    def __call__(self, name, frame, prediction):
        if frame is None:
            print(json.dumps(prediction))
        else:
            sys.stdout.write(frame[:, :, ::-1].tostring())


    def __enter__(self):
        return self
    def __exit__(self, exception_type, exception_value, traceback):
        pass

class DisplayOutputData(OutputData):
    def __init__(self, **kwargs):
        super(DisplayOutputData, self).__init__(None, **kwargs)
        self._fps = kwargs.get('output_fps', 25)
        self._window_name = 'Deepomatic'
        self._fullscreen = kwargs.get('fullscreen', False)

        if self._fullscreen:
            cv2.namedWindow(self._window_name, cv2.WINDOW_NORMAL)
            if imutils.is_cv2():
                prop_value = cv2.cv.CV_WINDOW_FULLSCREEN
            elif imutils.is_cv3():
                prop_value = cv2.WINDOW_FULLSCREEN
            else:
                assert('Unsupported opencv version')
            cv2.setWindowProperty(self._window_name,
                                  cv2.WND_PROP_FULLSCREEN,
                                  prop_value)

    def __call__(self, name, frame, prediction):
        if frame is None:
            logging.warning('No frame to output.')
        else:
            cv2.imshow(self._window_name, frame)
            if cv2.waitKey(self._fps) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                cv2.waitKey(1)
                sys.exit()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if cv2.waitKey(0) & 0xFF == ord('q'):
            cv2.destroyAllWindows()
            cv2.waitKey(1)

class JsonOutputData(OutputData):
    supported_formats = ['.json']

    @classmethod
    def is_valid(cls, descriptor):
        _, ext = os.path.splitext(descriptor)
        return ext in cls.supported_formats

    def __init__(self, descriptor, **kwargs):
        super(JsonOutputData, self).__init__(descriptor, **kwargs)
        self._i = 0
        # Check if the output is a wild card or not
        try:
            descriptor % self._i
            self._all_predictions = None
        except TypeError:
            self._all_predictions = {'tags': [], 'images': []}

    def __enter__(self):
        self._i = 0
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if self._all_predictions:
            json_path = os.path.splitext(self._descriptor)[0]
            save_json_to_file(self._all_predictions, json_path)

    def __call__(self, name, frame, prediction):
        self._i += 1
        # If the json is not a wildcard we store prediction to write then to file a the end with the __exit__
        if self._all_predictions:
            self._all_predictions['images'] += prediction['images']
            self._all_predictions['tags'] = list(set(self._all_predictions['tags'] + prediction['tags']))
        # Otherwise we write them to file directly
        else:
            json_path = os.path.splitext(self._descriptor % self._i)[0]
            save_json_to_file(prediction, json_path)
