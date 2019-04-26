import io
import cv2
import logging
try:
    from Queue import Empty, Full, Queue, LifoQueue
except ImportError:
    from queue import Empty, Full, Queue, LifoQueue


LOGGER = logging.getLogger(__name__)


class DeepoCLIException(Exception):
    pass


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
        if isinstance(queue, LifoQueue):
            queue.queue = []
        else:
            queue.queue.clear()

def write_frame_to_disk(frame, path):
    if frame.output_image is not None:
        LOGGER.info('Writing %s' % path)
        cv2.imwrite(path, frame.output_image)
    else:
        LOGGER.warning('No frame to output.')
    return
