from ...utils import PlatformCommand


class EngageAppCommand(PlatformCommand):
    """Engage App related commands."""

    from .create import CreateCommand
    from .delete import DeleteCommand
