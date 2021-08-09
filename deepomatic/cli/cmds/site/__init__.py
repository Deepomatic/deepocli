from ..utils import Command


class SiteCommand(Command):
    """
        Operations on your site (local or cloud)
        You can choose from the following commands to manage your local sites
    """

    # Offline
    from .use import UseCommand
    from .list import ListCommand
    from .load import LoadCommand
    from .save import SaveCommand
    from .uninstall import UninstallCommand
    from .rollback import RollbackCommand
    from .show import ShowCommand
    from .current import CurrentCommand

    # Using the API
    from .install import InstallCommand
    from .upgrade import UpgradeCommand
    from .create import CreateCommand
    from .update import UpdateCommand
    from .delete import DeleteCommand
    from .manifest import ManifestCommand

    from .work_order import WorkOrderCommand
    from .model import ModelCommand
