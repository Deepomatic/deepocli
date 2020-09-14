from ..utils import Command
from .utils import PlatformManager


class UploadCommand(Command):
    """
        Upload images
    """

    def run(self):
        return PlatformManager().upload()
