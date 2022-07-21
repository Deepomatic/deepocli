from ....utils import Command, valid_path
from ...utils import SiteManager


class UploadCommand(Command):
    """
        Upload a file at the provided upload_url
    """

    def setup(self, subparsers):
        parser = super(UploadCommand, self).setup(subparsers)
        batch = parser.add_mutually_exclusive_group(required=True)
        batch.add_argument('-i', "--batch_id", type=str, help='Batch id')
        batch.add_argument('-u', "--upload_url", type=str, help="Upload URL for the batch")
        parser.add_argument('-f', '--file', required=True, default=None, type=valid_path, help="path to the batch file")
        return parser

    def run(self, upload_url, batch_id, file, **kwargs):
        if upload_url:
            return SiteManager().upload_work_order_batch_by_url(upload_url, file)
        elif batch_id:
            return SiteManager().upload_work_order_batch_by_id(batch_id, file)
