from ..utils import Command
from .utils import PlatformManager


class TrainCommand(Command):
    """
        Launch a training
    """

    def run(self):
        return PlatformManager().train()
