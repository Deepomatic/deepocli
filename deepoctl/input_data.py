import os
import io
import cv2
import sys
import struct
from PIL import Image

import deepoctl.common as common

supported_image_formats = ['.bmp', '.jpeg', '.jpg', '.jpe', '.png']
supported_video_formats = ['.avi', '.mp4']
supported_protocols = ['rtsp']

all_supported_formats = supported_image_formats + supported_video_formats

def splitext(path):
    """os.path.splitext does not work for .tar.gz"""
    filename = os.path.basename(path)
    split_filename = filename.split('.')
    if len(split_filename) > 2:
        return '.'.join(split_filename[0:-2]), '.' + '.'.join(split_filename[-2:])
    return os.path.splitext(filename)

def is_supported(path):
    _, ext = splitext(path)
    return ext in all_supported_formats

def recurse(directory):
    for root, subdirs, files in os.walk(directory):
        for file in files:
            if is_supported(file):
                yield os.path.join(root, file)

def get_files(path):
    if os.path.isfile(path):
        if not is_supported(path):
            raise common.DeepoCTLException('Unsupported file extension: {}'.format(path))
        files = [path]
    elif os.path.isdir(path):
        files = recurse(path)
    else:
        raise common.DeepoCTLException('Path not found: {}'.format(path))
    return files

def get_streams(address):
    return [address]

def get_devices(device):
    return [device]

def get_inputs(path):
    if (os.path.exists(path)):
        return [('file', file) for file in get_files(path)]
    elif ('://' in path):
        return [('stream', stream) for stream in get_streams(path)]
    elif (path.isdigit()):
        return [('device', device) for device in get_devices(path)]
    else:
        raise Exception('Unsupported input')
    

# ---------------------------------------------------------------------------- #
# ---------------------------------------------------------------------------- #

class InputData(object):

    def __init__(self, path):
        self._path = path

    def fps(self):
        raise NotImplemented

    def get_frame_number(self):
        raise NotImplemented

    def get_frames(self):
        raise NotImplemented

    def prepare_draw(self, suffix):
        dirname = os.path.dirname(self._path)
        filename, ext = splitext(self._path)
        self._output_path = os.path.join(dirname, filename + '.' + suffix + ext)

    def add_frame(self, frame):
        raise NotImplemented

    def finalize_draw(self):
        raise NotImplemented

# ---------------------------------------------------------------------------- #

class ImageInputData(InputData):

    def __init__(self, path):
        super(ImageInputData, self).__init__(path)
        with open(path, 'rb') as f:
            self._img = f.read()

    def fps(self):
        return 0

    def get_frame_number(self):
        return 1

    def get_frames(self):
        yield self._img

    def prepare_draw(self, suffix):
        super(ImageInputData, self).prepare_draw(suffix)

    def add_frame(self, frame):
        cv2.imwrite(self._output_path, frame)

    def finalize_draw(self):
        pass

# ---------------------------------------------------------------------------- #

class VideoInputData(InputData):

    def __init__(self, path):
        super(VideoInputData, self).__init__(path)
        self._cap = cv2.VideoCapture(path)

    def fps(self):
        return self._cap.get(cv2.CAP_PROP_FPS)

    def get_frame_number(self):
        return self._cap.get(cv2.CAP_PROP_FRAME_COUNT)

    def get_frames(self):
        while(self._cap.isOpened()):
            _, frame = self._cap.read()
            if frame is None:
                break
            frame = Image.fromarray(frame[:, :, ::-1])
            with io.BytesIO() as output:
                frame.save(output, format="JPEG")
                yield output.getvalue()

    def prepare_draw(self, suffix):
        super(VideoInputData, self).prepare_draw(suffix)
        fourcc = [x for x in struct.pack('<I', int(self._cap.get(cv2.CAP_PROP_FOURCC)))]
        if sys.version_info >= (3, 0):
            fourcc = [str(chr(x)) for x in fourcc]
        width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*fourcc)
        self._out = cv2.VideoWriter(self._output_path, fourcc, self.fps(), (width, height))

    def add_frame(self, frame):
        self._out.write(frame)

    def finalize_draw(self):
        self._out.release()

# ---------------------------------------------------------------------------- #

def open_file(path):
    _, ext = splitext(path)
    if ext in supported_image_formats:
        return ImageInputData(path)
    elif ext in supported_video_formats:
        return VideoInputData(path)
    else:
        raise Exception('This should not happen')

def open_stream(address):
    protocol, _ = address.split(':')
    if (protocol in supported_protocols):
        return VideoInputData(address)
    else:
        raise Exception('Cannot read input stream')

def open_device(device):
    return VideoInputData(device)
