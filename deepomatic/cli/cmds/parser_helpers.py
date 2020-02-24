# Common parsers functions used by various commands
COMMON_GROUPS = {
    'input', 'output'
}


def add_common_cmd_group(parser, label):
    assert label in COMMON_GROUPS
    return parser.add_argument_group('{} arguments'.format(label.lower()))


def add_recursive_argument(parser):
    parser.add_argument('-R', '--recursive', dest='recursive', action='store_true',
                        help='If a directory input is used, goes through all files in subdirectories.')


def add_verbose_argument(parser):
    parser.add_argument('--verbose', dest='verbose', action='store_true',
                        help='Increase output verbosity.')
