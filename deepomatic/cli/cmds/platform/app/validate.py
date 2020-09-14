from ...utils import Command
from ..utils import PlatformManager


class ValidateCommand(Command):
    """
        Validate workflow
    """

    def run(self, path=".", **kwargs):
        # TODO: feedback
        return PlatformManager().validate(path)
