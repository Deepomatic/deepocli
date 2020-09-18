from ...utils import Command


class AppCommand(Command):
    """
        App related commands
    """

    from .create import CreateCommand
    from .delete import DeleteCommand
    from .update import UpdateCommand
