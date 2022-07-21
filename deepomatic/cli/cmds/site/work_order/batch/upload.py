from ....utils import Command, valid_path
from ...utils import SiteManager


class UploadCommand(Command):
    """
        Upload a file at the provided upload_url
    """

    def setup(self, subparsers):
        parser = super(UploadCommand, self).setup(subparsers)
        parser.add_argument('-u', "--upload_url", required=True, type=str, help="Upload URL for the batch")
        parser.add_argument('-f', '--file', required=False, default=None, type=valid_path, help="path to the batch file")
        return parser

    def run(self, upload_url, file, **kwargs):
        return SiteManager().upload_work_order_batch(upload_url, file)
