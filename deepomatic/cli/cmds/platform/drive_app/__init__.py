from ...utils import PlatformCommand


<<<<<<< HEAD:deepomatic/cli/cmds/platform/app/__init__.py
class AppCommand(PlatformCommand):
    """
        App related commands
    """
=======
class DriveAppCommand(Command):
    """DriveApp related commands."""
>>>>>>> master:deepomatic/cli/cmds/platform/drive_app/__init__.py

    from .create import CreateCommand
    from .delete import DeleteCommand
    from .update import UpdateCommand
