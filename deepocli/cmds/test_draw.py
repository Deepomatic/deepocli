import os
import tempfile
import requests

from deepocli.cli_parser import run

def download(url):
    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, os.path.basename(url))
    r = requests.get(url)
    with open(path, 'wb') as f:
        f.write(r.content)
    return path

image_url = 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/images/test.jpg'
image_path = download(image_url)

video_url = 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/videos/test.mp4'
video_path = download(video_url)


def test_e2e_image_draw_image():
    run(['draw', '-i', image_path, '--recognition_id', 'fashion-v4', '-o', '/tmp/test.jpeg'])

def test_e2e_image_draw_image_scores():
    run(['draw', '-i', image_path, '--recognition_id', 'fashion-v4', '-o', '/tmp/test_scores.jpeg', '--draw_scores'])

def test_e2e_image_draw_image_labels():
    run(['draw', '-i', image_path, '--recognition_id', 'fashion-v4', '-o', '/tmp/test_labels.jpeg', '--draw_labels'])

def test_e2e_image_draw_image_labels_and_scores():
    run(['draw', '-i', image_path, '--recognition_id', 'fashion-v4', '-o', '/tmp/test_labels.jpeg', '--draw_scores', '--draw_labels'])

def test_e2e_video_draw_video():
    run(['draw', '-i', video_path, '--recognition_id', 'fashion-v4', '-o', '/tmp/test.mp4'])

def test_e2e_video_draw_image():
    run(['draw', '-i', video_path, '--recognition_id', 'fashion-v4', '-o', '/tmp/test_%05d.jpeg'])

def test_e2e_video_draw_stdout():
    return
    run(['draw', '-i', video_path, '--recognition_id', 'fashion-v4', '-o', 'stdout', '--output_frame'])

def test_e2e_video_draw_window():
    return
    run(['draw', '-i', video_path, '--recognition_id', 'fashion-v4', '-o', 'window'])