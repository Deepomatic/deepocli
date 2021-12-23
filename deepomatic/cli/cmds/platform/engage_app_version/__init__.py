from ...utils import PlatformCommand


class EngageAppVersionCommand(PlatformCommand):
    """App version related commands."""

    from .create import CreateCommand
    from .clone import CloneCommand
    from .delete import DeleteCommand
