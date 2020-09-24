from ...utils import Command
from ..utils import SiteManager


class StatusCommand(Command):
    """
        Retrieve the intervention status
    """

    def setup(self, subparsers):
        parser = super(StatusCommand, self).setup(subparsers)
        parser.add_argument('-u', "--api_url", required=True, type=str, help="url of your Customer api")
        parser.add_argument('-i', '--intervention_id', required=True, type=str, help="Intervention id")
        return parser

    def run(self, api_url, intervention_id, **kwargs):
        return SiteManager().status_intervention(api_url, intervention_id)
