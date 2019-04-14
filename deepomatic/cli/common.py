import io
import logging


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
