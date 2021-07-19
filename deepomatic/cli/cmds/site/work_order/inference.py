from ...utils import Command, BuildDict, valid_path
from ..utils import SiteManager

import argparse
import base64


def build_data(type, value):
    if type == "text":
        return value
    elif type == "image":
        if value.startswith(('http://', 'https://')):
            return value
        else:
            try:
                path = valid_path(value)
                with open(path, 'r') as f:
                    encoded_string = base64.b64encode(f.read())
                    return 'data:image/jpg;base64,' + encoded_string.decode('utf-8')
            except Exception:
                raise Exception('image {} not supported'.format(value))

    elif type == "number":
        return value
    else:
        raise Exception("type {} not supported".format(type))


class BuildCustomerAPIInput(argparse.Action):
    """
    This class is used in argparse. It will transform a chain of name@type@values into a list of inputs for
    the CustomerAPI.
    """
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        self._nargs = nargs
        super(BuildCustomerAPIInput, self).__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        entries = []
        for kv in values:
            vals = kv.split("@")
            assert len(vals) == 3

            name = vals[0]
            e_type = vals[1]
            value = vals[2]

            item = {
                'name': name,
                'data':
                {
                    'type': e_type,
                    'value': build_data(e_type, value),
                }
            }
            entries.append(item)
        setattr(namespace, self.dest, entries)


class InferCommand(Command):
    """
        Make an inference on a work order
    """

    def setup(self, subparsers):
        parser = super(InferCommand, self).setup(subparsers)
        parser.add_argument('-u', "--api_url", required=True, type=str, help="url of your Customer api")
        parser.add_argument('-i', '--work_order_id', required=True, type=str, help="Work order id")
        parser.add_argument('-e', "--entries", dest='entries',
                            action=BuildCustomerAPIInput, nargs="+", metavar="NAME@TYPE@VAL",
                            help='Inputs that will be passed to the CustomerAPI. They should be in this format name@type@value',
                            required=True)
        parser.add_argument('-m', "--metadata", dest='metadata', required=True,
                            action=BuildDict, nargs="+", metavar="NAME:VAL",
                            help='Metadata for the inference in format name:value')
        return parser

    def run(self, api_url, work_order_id, entries, metadata, **kwargs):
        return SiteManager().make_work_order_inference(api_url, work_order_id, entries, metadata)
