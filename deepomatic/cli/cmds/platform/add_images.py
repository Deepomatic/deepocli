from deepomatic.cli.common import SUPPORTED_IMAGE_INPUT_FORMAT
from deepomatic.cli.cmds import parser_helpers
from deepomatic.cli.cmds.utils import Command
from deepomatic.cli.cmds.platform.utils import AddImageManager


class AddImagesCommand(Command):
    """
        Upload simple images to Deepomatic Platform.
        Typical usage is: deepo platform add_images -i img.png -p myproject -o myorg
    """

    def setup(self, subparsers):
        parser = super(AddImagesCommand, self).setup(subparsers)

        # Define studio group for add_images
        group = parser.add_argument_group('studio arguments')
        help_msg = "Deepomatic Studio project name. Note: the argument --dataset was changed to --project"
        group.add_argument('-p', '--project', required=True, help=help_msg, type=str)
        group.add_argument('-o', '--org', required=True, help="Deepomatic Studio org slug.", type=str)

        input_group = parser_helpers.add_common_cmd_group(parser, 'input')
        # Define input group for add_images
        input_group.add_argument('-i', '--input', type=str, nargs='+', required=True,
                                 help="One or several input path, either an image file (*{}),"
                                 " a directory, or a Studio txt (*.txt).".format(
                                     ', *'.join(SUPPORTED_IMAGE_INPUT_FORMAT)
                                 ))
        input_group.add_argument('--txt', dest='txt_file', action='store_true',
                                 help='Look for txt files instead of images.')
        parser_helpers.add_recursive_argument(input_group)

        parser.add_argument('--set_metadata_path', dest='set_metadata_path',
                            action='store_true',
                            help='Add the relative path as metadata.')
        return parser

    def run(self, **kwargs):
        return AddImageManager().upload(kwargs)
