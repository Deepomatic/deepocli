from ...utils import Command
from ..utils import SiteManager


class StatusCommand(Command):
    """
        Retrieve the work order status
    """

    def setup(self, subparsers):
        parser = super(StatusCommand, self).setup(subparsers)
        parser.add_argument('-u', "--api_url", required=True, type=str, help="url of your Customer api")
        parser.add_argument('-i', '--work_order_id', required=True, type=str, help="Work order id")
        return parser

    def run(self, api_url, work_order_id, **kwargs):
        return SiteManager().status_work_order(api_url, work_order_id)
