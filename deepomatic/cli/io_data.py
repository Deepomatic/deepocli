import os
import sys
import json
import imutils
import logging
import cv2
import time
import threading
from tqdm import tqdm

try:
    from Queue import Queue, LifoQueue, Empty
except ImportError:
    from queue import Queue, LifoQueue, Empty

INPUT_QUEUE_MAX_SIZE = 50

def print_log(log):
    """Uses tqdm helper function to ensure progressbar stays at the bottom."""
    tqdm.write(log)

def get_input(descriptor, kwargs):
    if (descriptor is None):
        raise NameError('No input specified. use -i flag')
    elif os.path.exists(descriptor):
        if os.path.isfile(descriptor):
            if ImageInputData.is_valid(descriptor):
                return ImageInputData(descriptor, **kwargs)
            elif VideoInputData.is_valid(descriptor):
                return VideoInputData(descriptor, **kwargs)
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
        if os.path.isdir(descriptor):
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

def input_loop(kwargs, worker_thread):
    inputs = get_input(kwargs.get('input', 0), kwargs)

    # Initialize progress bar
    max_value = inputs.get_frame_count()
    max_value = int(max_value) if max_value >= 0 else None  # ensure it's int for tqdm display
    pbar = tqdm(total=max_value)

    # For realtime, queue should be LIFO
    input_queue = LifoQueue() if inputs.is_infinite() else Queue()
    output_queue = LifoQueue() if inputs.is_infinite() else Queue()

    worker = worker_thread(input_queue, output_queue, **kwargs)
    worker.start()
    output_thread = OutputThread(output_queue, on_progress=lambda i: pbar.update(1), **kwargs)
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

            while input_queue.qsize() > INPUT_QUEUE_MAX_SIZE:
                time.sleep(1)

            input_queue.put(frame)

        # notify worker_thread that input stream is over
        input_queue.put(None)

        worker.join()
        output_thread.join()

        # Close the tqdm progress bar
        time.sleep(0.1)
        pbar.n = max_value
        pbar.refresh()
        pbar.close()

    except KeyboardInterrupt:
        logging.info('Stopping input')
        while not input_queue.empty():
            try:
                input_queue.get(False)
                input_queue.task_done()
            except Empty:
                break
        input_queue.put(None)

        worker.join()
        output_thread.join()

class OutputThread(threading.Thread):
    def __init__(self, queue, on_progress=None, **kwargs):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.queue = queue
        self.args = kwargs
        self.on_progress = on_progress

    def run(self):
        i = 0
        with get_output(self.args.get('output', None), self.args) as output:
            try:
                while True:
                    i += 1
                    data = self.queue.get()
                    if data is None:
                        self.queue.task_done()
                        return

                    output(*data)
                    if (self.on_progress is not None):
                        self.on_progress(i)
                    self.queue.task_done()
            except KeyboardInterrupt:
                pass

class InputData(object):
    def __init__(self, descriptor,  **kwargs):
        self._descriptor = descriptor
        self._args = kwargs
        self._name, _ = os.path.splitext(os.path.basename(str(descriptor)))
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
            return self._name, cv2.imread(self._descriptor, 1)
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
                return self._name % self._i, frame
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

        if self.is_valid(descriptor):
            _paths = [os.path.join(descriptor, name) for name in os.listdir(descriptor)]
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

class OutputData(object):
    def __init__(self, descriptor, **kwargs):
        self._descriptor = descriptor
        self._args = kwargs

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


class VideoOutputData(OutputData):
    supported_formats = ['.avi', '.mp4']

    @classmethod
    def is_valid(cls, descriptor):
        _, ext = os.path.splitext(descriptor)
        return ext in cls.supported_formats

    def __init__(self, descriptor, **kwargs):
        super(VideoOutputData, self).__init__(descriptor, **kwargs)
        _, ext = os.path.splitext(descriptor)
        if ext is 'mjpg':
            fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')
        else:
            fourcc = cv2.VideoWriter_fourcc('X', '2', '6', '4')
        self._fourcc = fourcc
        self._fps = kwargs.get('output_fps', 25)
        self._writer = None

    def __enter__(self):
        if self._writer is not None:
            self._writer.release()
        self._writer = None
        return self

    def __exit__(self, exception_type, exception_value, traceback):
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

class DrawOutputData(OutputData):

    def __init__(self, **kwargs):
        super(DrawOutputData, self).__init__(None, **kwargs)
        self._draw_labels = kwargs.get('draw_labels', False)
        self._draw_scores = kwargs.get('draw_scores', False)

    def __call__(self, name, frame, prediction, font_scale=0.5):
        frame = frame.copy()
        h = frame.shape[0]
        w = frame.shape[1]
        for predicted in prediction:
            label = ''
            if self._draw_labels:
                label += predicted['label_name']
            if self._draw_labels and self._draw_scores:
                label += ' '
            if self._draw_scores:
                label += str(predicted['score'])

            roi = predicted['roi']
            if roi is None:
                pass
            else:
                bbox = roi['bbox']
                xmin = int(bbox['xmin'] * w)
                ymin = int(bbox['ymin'] * h)
                xmax = int(bbox['xmax'] * w)
                ymax = int(bbox['ymax'] * h)
                region_id = roi['region_id']
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
        for predicted in prediction:
            label = predicted['label_name']
            roi = predicted['roi']
            if (roi is None):
                pass
            else:
                bbox = roi['bbox']
                xmin = int(float(bbox['xmin']) * w)
                ymin = int(float(bbox['ymin']) * h)
                xmax = int(float(bbox['xmax']) * w)
                ymax = int(float(bbox['ymax']) * h)

                if (self._method == 'black'):
                    cv2.rectangle(frame,(xmin, ymin),(xmax, ymax),(0,0,0),-1)
                else:
                    face = frame[ymin:ymax, xmin:xmax]
                    if (self._method == 'gaussian'):
                        face = cv2.GaussianBlur(face, (15, 15), self._strength)
                    elif (self._method == 'pixel'):
                        small = cv2.resize(face, (0,0), fx=1./min((xmax - xmin), self._strength), fy=1./min((ymax - ymin), self._strength))
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
            with open(path, 'w') as file:
                print_log('Writing %s' % path)
                json.dump(prediction, file)
