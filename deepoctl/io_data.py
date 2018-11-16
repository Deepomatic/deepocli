import os
import sys
import json
import imutils
import cv2
import threading
from Queue import Queue, LifoQueue, Empty

def get_input(descriptor):
    if (descriptor is None):
        raise NameError('No input specified. use -i flag')
    elif os.path.exists(descriptor):
        if os.path.isfile(descriptor):
            if ImageInputData.is_valid(descriptor):
                return ImageInputData(descriptor)
            elif VideoInputData.is_valid(descriptor):
                return VideoInputData(descriptor)
            else:
                raise NameError('Unsupported input file type')
        elif os.path.isdir(descriptor):
            return DirectoryInputData(descriptor)
        else:
            raise NameError('Unknown input path')
    elif descriptor.isdigit():
        return DeviceInputData(descriptor)
    elif StreamInputData.is_valid(descriptor):
        return StreamInputData(descriptor)
    else:
        raise NameError('Unknown input')

def get_output(descriptor, args):
    if descriptor is not None:
        if os.path.isdir(descriptor):
            return DirectoryOutputData(descriptor, **args)
        elif ImageOutputData.is_valid(descriptor):
            return ImageOutputData(descriptor, **args)
        elif VideoOutputData.is_valid(descriptor):
            return VideoOutputData(descriptor, **args)
        elif JsonOutputData.is_valid(descriptor):
            return VideoOutputData(descriptor, **args)
        elif descriptor == 'stdout':
            return StdOutputData(**args)
        else:
            raise NameError('Unknown output')
    else:
        return DisplayOutputData(**args)

def input_loop(args, worker_thread):
    inputs = get_input(args.get('input', 0))

    # For realtime, queue should be LIFO
    input_queue = LifoQueue() if inputs.is_infinite() else Queue()
    output_queue = LifoQueue() if inputs.is_infinite() else Queue()

    worker = worker_thread(input_queue, output_queue, **args)
    output_thread = OutputThread(output_queue, **args)

    worker.start()
    output_thread.start()

    for frame in inputs:
        if inputs.is_infinite():
            # Discard all previous inputs
            while not input_queue.empty():
                try:
                    input_queue.get(False)
                except Empty:
                    continue
                input_queue.task_done()
        input_queue.put(frame)

    worker.join()
    output_thread.join()

class OutputThread(threading.Thread):
    def __init__(self, queue, **kwargs):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.queue = queue
        self.args = kwargs

    def run(self):
        with get_output(self.args.get('output', None), self.args) as output:
            while True:
                frame = self.queue.get()
                if frame is None:
                    return
                should_stop = output(frame)
                self.queue.task_done()
                if should_stop:
                    return

class InputData(object):
    def __init__(self, descriptor):
        self._descriptor = descriptor

    def __iter__(self):
        return self

    def next(self):
        raise StopIteration

    def get_fps(self):
        raise NotImplementedError

    def get_frame_number(self):
        raise NotImplementedError

    def is_infinite(self):
        raise NotImplementedError


class ImageInputData(InputData):
    supported_formats = ['.bmp', '.jpeg', '.jpg', '.jpe', '.png']

    @classmethod
    def is_valid(cls, descriptor):
        _, ext = os.path.splitext(descriptor)
        return os.path.exists(descriptor) and ext in cls.supported_formats

    def __init__(self, descriptor):
        super(ImageInputData, self).__init__(descriptor)
        self.first = None

    def __iter__(self):
        self.first = True
        return self

    def next(self):
        if self.first:
            self.first = False
            return cv2.imread(self._descriptor, 1)
        else:
            raise StopIteration

    def get_fps(self):
        return 0

    def get_frame_number(self):
        return 1

    def is_infinite(self):
        return False


class VideoInputData(InputData):
    supported_formats = ['.avi', '.mp4', '.webm']

    @classmethod
    def is_valid(cls, descriptor):
        _, ext = os.path.splitext(descriptor)
        return os.path.exists(descriptor) and ext in cls.supported_formats

    def __init__(self, descriptor):
        super(VideoInputData, self).__init__(descriptor)
        self._cap = None

    def __iter__(self):
        if (self._cap is not None):
            self._cap.release()
        self._cap = cv2.VideoCapture(self._descriptor)
        return self

    def next(self):
        if (self._cap.isOpened()):
            _, frame = self._cap.read()
            if frame is None:
                self._cap.release()
                raise StopIteration
            else:
                return frame
        self._cap.release()
        raise StopIteration

    def get_fps(self):
        return self._cap.get(cv2.CAP_PROP_FPS)

    def get_frame_number(self):
        return self._cap.get(cv2.CAP_PROP_FRAME_COUNT)

    def is_infinite(self):
        return False

class DirectoryInputData(InputData):
    @classmethod
    def is_valid(cls, descriptor):
        return (os.path.exists(descriptor) and os.path.isdir(descriptor))

    def __init__(self, descriptor):
        super(DirectoryInputData, self).__init__(descriptor)
        self._current = None
        self._files = []
        self._inputs = []
        if (self.is_valid(descriptor)):
            print('valid', os.listdir(descriptor))
            _paths = [os.path.join(descriptor, name) for name in os.listdir(descriptor)]
            _files = [
                ImageInputData(path) if ImageInputData.is_valid(path) else
                VideoInputData(path) if VideoInputData.is_valid(path) else
                None for path in _paths if os.path.isfile(path)]
            self._inputs = [_input for _input in _files if _input is not None]

    def _gen(self):
        for source in self._inputs:
            for frame in source:
                yield frame
    def __iter__(self):
        self.gen = self._gen()
        return self

    def next(self):
        try:
            return next(self.gen)
        except StopIteration:
            return None

    def get_frame_number(self):
        return sum([_input.get_frame_number() for _input in self._inputs])
    
    def get_fps(self):
        return 1

    def is_infinite(self):
        return False

class StreamInputData(VideoInputData):
    supported_protocols = ['rtsp', 'http', 'https']

    @classmethod
    def is_valid(cls, descriptor):
        return '://' in descriptor and descriptor.split('://')[0] in cls.supported_protocols

    def __init__(self, descriptor):
        super(StreamInputData, self).__init__(descriptor)

    def is_infinite(self):
        return True

class DeviceInputData(VideoInputData):

    @classmethod
    def is_valid(cls, descriptor):
        return descriptor.isdigit()

    def __init__(self, descriptor):
        super(DeviceInputData, self).__init__(int(descriptor))

    def is_infinite(self):
        return True

class OutputData(object):
    def __init__(self, descriptor, **kwargs):
        self._descriptor = descriptor
        self._args = kwargs

    def __enter__(self):
        raise NotImplementedError

    def __exit__(self, exception_type, exception_value, traceback):
        raise NotImplementedError

    def __call__(self, output):
        raise NotImplementedError


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

    def __call__(self, frame):
        path = self._descriptor
        try:
            path = path % self._i
        except TypeError:
            pass
        finally:
            self._i += 1
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
        if (self._writer is not None):
            self._writer.release()
        self._writer = None
        return self
    
    def __exit__(self, exception_type, exception_value, traceback):
        self._writer.release()

    def __call__(self, frame):
        if (self._writer is None):
            self._writer = cv2.VideoWriter(self._descriptor, 
                self._fourcc,
                self._fps,
                (frame.shape[1], frame.shape[0]))
        self._writer.write(frame)


class DrawOutputData(OutputData):

    def __init__(self, **kwargs):
        super(DrawOutputData, self).__init__(None, **kwargs)
        self._threshold = float(kwargs.get('threshold', 0.7))
        self._draw_label = kwargs.get('draw_label', False)
        self._draw_score = kwargs.get('draw_score', False)

    def __call__(self, frame_and_detection, font_scale=0.5):
        frame, detection = frame_and_detection
        frame = frame.copy()
        h = frame.shape[0]
        w = frame.shape[1]
        for predicted in detection:
            label = ""
            if self._draw_label:
                label += predicted['label_name']
            if self._draw_label and self._draw_score:
                label += " "
            if self._draw_score:
                label += predicted['score']

            roi = predicted['roi']
            if roi is None:
                pass
            elif predicted['score'] < self._threshold:
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
        return frame

    def __enter__(self):
        return self
    def __exit__(self, exception_type, exception_value, traceback):
        pass

class BlurOutputData(OutputData):

    def __init__(self, **kwargs):
        super(BlurOutputData, self).__init__(None, **kwargs)
        self._threshold = float(kwargs.get('threshold', 0.7))
        self._method = kwargs.get('blur_method', 'pixel')
        self._strength = kwargs.get('blur_strength', 10)

    def __call__(self, frame_and_detection, font_scale=0.5):
        frame, detection = frame_and_detection
        frame = frame.copy()
        h = frame.shape[0]
        w = frame.shape[1]
        for predicted in detection:
            label = predicted['label_name']
            roi = predicted['roi']
            if (roi is None):
                pass
            elif predicted['score'] < self._threshold:
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
                        face = cv2.GaussianBlur(face,(15, 15), self._strength)
                    elif (self._method == 'pixel'):
                        small = cv2.resize(face, (0,0), fx=1./min((xmax - xmin), self._strength), fy=1./min((ymax - ymin), self._strength))
                        face = cv2.resize(small, ((xmax - xmin), (ymax - ymin)), interpolation=cv2.INTER_NEAREST)
                    frame[ymin:ymax, xmin:xmax] = face
        return frame

    def __enter__(self):
        return self
    def __exit__(self, exception_type, exception_value, traceback):
        pass

class StdOutputData(OutputData):
    """
        To use with vlc : python scripts/deepoctl draw -i 0 -o stdout | vlc --demux=rawvideo --rawvid-fps=25 --rawvid-width=640 --rawvid-height=480 --rawvid-chroma=RV24 - --sout "#display"
    """
    def __init__(self, **kwargs):
        super(StdOutputData, self).__init__(None, **kwargs)

    def __call__(self, frame):
        data = frame[:, :, ::-1].tostring()
        sys.stdout.write(data)

    def __enter__(self):
        return self
    def __exit__(self, exception_type, exception_value, traceback):
        pass

class DisplayOutputData(OutputData):
    def __init__(self, **kwargs):
        super(DisplayOutputData, self).__init__(None, **kwargs)
        self._fps = kwargs.get('output_fps', 25)
        self._window_name = "Deepomatic feed"
        self._fullscreen = kwargs.get('fullscreen', False)

        if self._fullscreen:
            cv2.namedWindow(self._window_name, cv2.WINDOW_NORMAL)
            if imutils.is_cv2():
                prop_value = cv2.cv.CV_WINDOW_FULLSCREEN
            elif imutils.is_cv3():
                prop_value = cv2.WINDOW_FULLSCREEN
            else:
                assert("Unsupported opencv version")
            cv2.setWindowProperty(self._window_name,
                                  cv2.WND_PROP_FULLSCREEN,
                                  prop_value)

    def __call__(self, frame):
        cv2.imshow(self._window_name, frame)
        if cv2.waitKey(self._fps) & 0xFF == ord('q'):
            return True


    def __enter__(self):
        return self
    def __exit__(self, exception_type, exception_value, traceback):
        pass

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

    def __call__(self, detection):
        path = self._descriptor
        try:
            path = path % self._i
        except TypeError:
            pass
        finally:
            self._i += 1
            with open(path, 'w') as file:
                json.dump(file, detection)
