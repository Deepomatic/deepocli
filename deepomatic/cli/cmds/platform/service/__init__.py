from ...utils import Command


class ServiceCommand(Command):
    """
        Service related commands
    """

    from .create import CreateCommand
    from .delete import DeleteCommand
