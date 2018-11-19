import argparse
from deepoctl.cmds.infer import main as infer
from deepoctl.cmds.draw import main as draw
from deepoctl.cmds.blur import main as blur
from deepoctl.io_data import ImageInputData, VideoInputData, StreamInputData

def parse_args(args):
    argparser = argparse.ArgumentParser(prog='deepoctl')
    subparsers = argparser.add_subparsers(dest='command')
    subparsers.required = True

    infer_parser = subparsers.add_parser('infer', help="Run inference on a file or directory and outputs a JSON file with the recognition results.")
    infer_parser.set_defaults(func=infer)

    draw_parser = subparsers.add_parser('draw', help="Generate new images and videos with inference results drawn on them. Runs inference if JSON has not yet been generated.")
    draw_parser.set_defaults(func=draw)

    blur_parser = subparsers.add_parser('blur', help="Generate new images and videos with inference results blurred out. Runs inference if JSON has not yet been generated.")
    blur_parser.set_defaults(func=blur)

    parsers = [infer_parser, draw_parser, blur_parser]
    for parser in parsers:
        parser.add_argument('-i', '--input', help="Path on which inference should be run. It can be an image (supported formats: *{}), a video (supported formats: *{}) or a directory. If the given path is a directory, it will recursively run inference on all the supported files in this directory.".format(', *'.join(ImageInputData.supported_formats), ', *'.join(VideoInputData.supported_formats)))
        parser.add_argument('-o', '--output', help="Path in which output should be written. It can be an image (supported formats: *{}), a video (supported formats: *{}) or a directory.".format(', *'.join(ImageInputData.supported_formats), ', *'.join(VideoInputData.supported_formats)))
        parser.add_argument('-r', '--recognition_id', help="Recognition version ID")
        parser.add_argument('-u', '--amqp_url', help="AMQP url")
        parser.add_argument('-k', '--routing_key', help="Recognition routing key")
        parser.add_argument('-t', '--threshold', help="Threshold under which inference result should be ignored", default=0.7)
        parser.add_argument('--output_frame', help="Output frame data if std output", action="store_true")
        parser.add_argument('--output_fps', help="Output fps", default=25)
        parser.add_argument('--fullscreen', help="Fullscreen if window output", action="store_true")

    draw_parser.add_argument('--draw_scores', help="Draw scores if draw output", action="store_true")
    draw_parser.add_argument('--draw_labels', help="Draw labels if draw output", action="store_true")

    blur_parser.add_argument('--blur_method', help="Blur method if blur output", default="pixel")
    blur_parser.add_argument('--blur_strength', help="Blur method if blur output", default=10)

    return argparser.parse_args(args)

def run(args):
    args = parse_args(args)
    args.func(vars(args))
