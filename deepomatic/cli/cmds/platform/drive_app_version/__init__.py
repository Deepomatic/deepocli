from ...utils import PlatformCommand


class DriveAppVersionCommand(PlatformCommand):
    """DriveApp version related commands."""

    from .create import CreateCommand
    from .update import UpdateCommand
    from .delete import DeleteCommand
