from ...utils import Command


class DriveAppVersionCommand(Command):
    """DriveApp version related commands."""

    from .create import CreateCommand
    from .update import UpdateCommand
    from .delete import DeleteCommand
