from ...utils import Command
from ..utils import PlatformManager


class CreateCommand(Command):
    """
        Create a new service
    """

    def setup(self, subparsers):
        parser = super(CreateCommand, self).setup(subparsers)
        parser.add_argument('-n', '--name', required=True, type=str, help="Service name")
        parser.add_argument('-a', '--app_id', required=True, type=str, help="App id for this service")
        parser.add_argument('-w', '--circus_watchers', nargs="*", type=str,
                            help="List of circus watchers", default=[])
        return parser

    def run(self, app_id, name, circus_watchers, **kwargs):
        if not circus_watchers and name in ['worker-nn', 'camera-server',
                                            'workflow-server']:
            # It is important to set it for those services
            circus_watchers = [name]
        return PlatformManager().create_service(app_id=app_id, name=name,
                                                circus_watchers=circus_watchers)
