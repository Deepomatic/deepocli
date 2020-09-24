from ...utils import Command


class InterventionCommand(Command):
    """
        Intervention related commands
    """

    from .create import CreateCommand
    from .status import StatusCommand
    from .inference import InferCommand
    from .delete import DeleteCommand
