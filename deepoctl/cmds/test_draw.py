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

def test_outputs(input):
    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, os.path.basename(input))

    def test_output(output):
        args = ['draw', '-i', image_path, '--recognition_id', 'fashion-v4', '-o']
        args.extend(output)
        print('test %s' % args)
        run(args)

    outputs = [
        ['stdout'],
    #    ['stdout', '--output_frame'],
        ['/tmp/test.json'],
        ['/tmp/test.jpeg'],
        ['/tmp/test_scores.jpeg', '--draw_scores'],
        ['/tmp/test_labels.jpeg', '--draw_labels'],
        ['/tmp/test_scores_labels.jpeg', '--draw_scores', '--draw_labels'],
        ['/tmp/test_%05d.jpeg'],
        ['window']
    ]

    [test_output(output) for output in outputs]



if __name__ == "__main__":
    image_url = 'https://storage.googleapis.com/dp-vulcan/tests/deepoctl/test.jpg'
    video_url = 'https://storage.googleapis.com/dp-vulcan/tests/deepoctl/test.mp4'
    
    image_path = download(image_url)

    test_outputs(image_path)