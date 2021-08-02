from ...utils import Command


class WorkOrderCommand(Command):
    """
        Work order related commands
    """

    from .create import CreateCommand
    from .status import StatusCommand
    from .inference import InferCommand
    from .delete import DeleteCommand
