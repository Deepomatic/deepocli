from ...utils import Command


class EngageAppCommand(Command):
    """
        Engage App related commands
    """

    from .create import CreateCommand
    from .delete import DeleteCommand
    from .update import UpdateCommand
