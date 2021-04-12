from ..utils import Command
from deepomatic.cli.lib.system import SystemManager


class SystemCommand(Command):
    """
        System command
    """

    class CheckCommand(Command):
        """
            Check the system
        """

        def run(self, **kwargs):
            SystemManager().check()
