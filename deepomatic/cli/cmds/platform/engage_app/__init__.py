from ...utils import PlatformCommand


class EngageAppCommand(Command):
    """Engage App related commands."""

    from .create import CreateCommand
    from .delete import DeleteCommand
