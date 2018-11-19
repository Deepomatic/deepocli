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

image_url = 'https://storage.googleapis.com/dp-vulcan/tests/deepoctl/test.jpg'
image_path = download(image_url)

video_url = 'https://storage.googleapis.com/dp-vulcan/tests/deepoctl/test.mp4'
video_path = download(video_url)


def test_e2e_image_infer_stdout():
    run(['infer', '-i', image_path, '--recognition_id', 'fashion-v4', '-o', 'stdout'])

def test_e2e_image_infer_json():
    run(['infer', '-i', image_path, '--recognition_id', 'fashion-v4', '-o', '/tmp/test.json'])

def test_e2e_video_infer_stdout():
    run(['infer', '-i', video_path, '--recognition_id', 'fashion-v4', '-o', 'stdout'])

def test_e2e_video_infer_json():
    run(['infer', '-i', video_path, '--recognition_id', 'fashion-v4', '-o', '/tmp/test_%05d.json'])