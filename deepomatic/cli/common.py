import io
import os
import cv2
import logging
try:
    import Queue as queue
except ImportError:
    import queue as queue

from deepomatic.cli.version import __title__, __version__

Full = queue.Full
Queue = queue.Queue
Empty = queue.Empty

LOGGER = logging.getLogger(__name__)
SUPPORTED_STUDIO_INPUT_FORMAT = ['.txt']
SUPPORTED_IMAGE_INPUT_FORMAT = ['.bmp', '.jpeg', '.jpg', '.jpe', '.png', '.tif', '.tiff']
SUPPORTED_VIDEO_INPUT_FORMAT = ['.avi', '.mp4', '.webm', '.mjpg']
SUPPORTED_FILE_INPUT_FORMAT = SUPPORTED_IMAGE_INPUT_FORMAT + SUPPORTED_VIDEO_INPUT_FORMAT
SUPPORTED_PROTOCOLS_INPUT = ['rtsp', 'http', 'https']
SUPPORTED_IMAGE_OUTPUT_FORMAT = SUPPORTED_IMAGE_INPUT_FORMAT
SUPPORTED_VIDEO_OUTPUT_FORMAT = ['.avi', '.mp4']
REQUESTS_DEFAULT_TIMEOUT = float(os.getenv("REQUESTS_TIMEOUT", "40."))
DEFAULT_USER_AGENT_PREFIX = '{}/{}'.format(__title__, __version__)

BGR_TO_COLOR_SPACE = {
    'RGB': cv2.COLOR_BGR2RGB,
    'YUV': cv2.COLOR_BGR2YUV,
    'YUV420': cv2.COLOR_BGR2YUV_I420,
    'HSV': cv2.COLOR_BGR2HSV,
    'GRAY': cv2.COLOR_BGR2GRAY,
}

SUPPORTED_VIDEO_OUTPUT_COLOR_SPACE = list(BGR_TO_COLOR_SPACE.keys()) + ['BGR']

SUPPORTED_FOURCC = {
    '.mp4': ['mp4v', 'avc1'],
    '.avi': ['XVID', 'MJPG']
}


class TqdmToLogger(io.StringIO):
    """Tqdm output stream to play nice with logger."""
    logger = None
    level = None
    buf = ''

    def __init__(self, logger, level=None):
        super(TqdmToLogger, self).__init__()
        self.logger = logger
        self.level = level or logging.INFO

    def write(self, buf):
        self.buf = buf.strip('\r\n\t ')

    def flush(self):
        self.logger.log(self.level, self.buf)


def clear_queue(queue):
    with queue.mutex:
        queue.queue.clear()


def write_frame_to_disk(frame, path):
    if frame.output_image is not None:
        if os.path.isfile(path):
            LOGGER.warning('File {} already exists. Skipping it.'.format(path))
        else:
            LOGGER.debug('Writing file {} to disk'.format(path))
            cv2.imwrite(path, frame.output_image)
    else:
        LOGGER.warning('No frame to output.')
    return
