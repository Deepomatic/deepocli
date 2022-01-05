from ...utils import PlatformCommand


class DriveAppCommand(Command):
    """DriveApp related commands."""

    from .create import CreateCommand
    from .delete import DeleteCommand
    from .update import UpdateCommand
