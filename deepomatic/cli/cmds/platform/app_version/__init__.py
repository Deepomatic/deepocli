from ...utils import Command


class AppVersionCommand(Command):
    """
        App version related commands
    """

    from .create import CreateCommand
    from .update import UpdateCommand
    from .delete import DeleteCommand
