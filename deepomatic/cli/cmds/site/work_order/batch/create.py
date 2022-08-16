from ....utils import Command, valid_path
from ...utils import SiteManager


class CreateCommand(Command):
    """
        Create a new work order batch
    """

    def setup(self, subparsers):
        parser = super(CreateCommand, self).setup(subparsers)
        parser.add_argument('-u', "--api_url", required=True, type=str, help="url of your Customer api")
        parser.add_argument('-n', "--name", required=False, type=str, help="name of the batch")
        parser.add_argument('-f', '--file', required=False, default=None, type=valid_path, help="path to the batch file")
        return parser

    def run(self, api_url, name, file, **kwargs):
        return SiteManager().create_work_order_batch(api_url, file, name)
