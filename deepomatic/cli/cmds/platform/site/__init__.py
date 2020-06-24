from ...utils import Command


class SiteCommand(Command):
    """
        Site related commands
    """

    from .create import CreateCommand
    from .update import UpdateCommand
