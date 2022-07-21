from ...utils import Command, SiteManager

class StatusCommand(Command):
    """
        Retrieve the work order batch status
    """

    def setup(self, subparsers):
        parser = super(StatusCommand, self).setup(subparsers)
        parser.add_argument('-u', "--api_url", required=True, type=str, help="url of your Customer api")
        parser.add_argument('-i', '--work_order_batch_id', required=True, type=str, help="Work order id")
        return parser

    def run(self, api_url, work_order_batch_id, **kwargs):
        return SiteManager().status_work_order_batch(api_url, work_order_batch_id)
