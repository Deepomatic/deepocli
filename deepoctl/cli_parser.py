import argparse
from deepoctl.cmds.infer import main as infer
from deepoctl.cmds.draw import main as draw
from deepoctl.input_data import supported_image_formats, supported_video_formats

def parse_args(args):
    argparser = argparse.ArgumentParser(prog='deepoctl')
    subparsers = argparser.add_subparsers(dest='command')
    subparsers.required = True

    infer_parser = subparsers.add_parser('infer', help="Run inference on a file or directory and outputs a JSON file with the recognition results.")
    infer_parser.add_argument('path', help="Path on which inference should be run. It can be an image (supported formats: *{}), a video (supported formats: *{}) or a directory. If the given path is a directory, it will recursively run inference on all the supported files in this directory.".format(', *'.join(supported_image_formats), ', *'.join(supported_video_formats)))
    infer_parser.add_argument('-r', '--recognition_id', help="Recognition version ID")
    infer_parser.set_defaults(func=infer)

    infer_parser = subparsers.add_parser('draw', help="Generate new images and videos with inference results drawn on them. Runs inference if JSON has not yet been generated.")
    infer_parser.add_argument('path', help="Path on which inference should be run. It can be an image (supported formats: *{}), a video (supported formats: *{}) or a directory. If the given path is a directory, it will recursively run inference on all the supported files in this directory.".format(', *'.join(supported_image_formats), ', *'.join(supported_video_formats)))
    infer_parser.add_argument('-r', '--recognition_id', help="Recognition version ID")
    infer_parser.set_defaults(func=draw)

    return argparser.parse_args(args)

def run(args):
    args = parse_args(args)
    args.func(args)
