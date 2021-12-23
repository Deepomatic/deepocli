from ...utils import PlatformCommand


class AppVersionCommand(PlatformCommand):
    """
        App version related commands
    """

    from .create import CreateCommand
    from .update import UpdateCommand
    from .delete import DeleteCommand
