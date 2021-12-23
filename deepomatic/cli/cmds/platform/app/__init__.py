from ...utils import PlatformCommand


class AppCommand(PlatformCommand):
    """
        App related commands
    """

    from .create import CreateCommand
    from .delete import DeleteCommand
    from .update import UpdateCommand
