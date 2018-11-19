import os
import tempfile
import requests

from deepoctl.cli_parser import run

def download(url):
    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, os.path.basename(url))
    r = requests.get(url)
    with open(path, 'wb') as f:
        f.write(r.content)
    return path

def test_outputs_for_image():
    image_url = 'https://storage.googleapis.com/dp-vulcan/tests/deepoctl/test.jpg'
    image_path = download(image_url)

    def test_output(output):
        args = ['blur', '-i', image_path, '--recognition_id', 'fashion-v4', '-o']
        args.extend(output)
        print('test %s' % args)
        run(args)

    outputs = [
    #    ['stdout', '--output_frame'],
        ['/tmp/test.jpeg'],
        ['/tmp/test_pixel.jpeg', '--blur_method', 'pixel'],
        ['/tmp/test_pixel_4.jpeg', '--blur_strength',  '4'],
    #    ['window']
    ]

    [test_output(output) for output in outputs]