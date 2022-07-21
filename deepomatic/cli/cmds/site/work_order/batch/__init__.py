from ....utils import Command


class BatchCommand(Command):
    """
        Work order related commands
    """

    from .create import CreateCommand
    from .status import StatusCommand
    from .delete import DeleteCommand
