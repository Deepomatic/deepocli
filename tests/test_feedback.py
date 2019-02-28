# -*- coding: utf-8 -*-
import os
import tempfile
import requests

from deepomatic.cli.cli_parser import run

def download(tmpdir, url, filepath):
    path = os.path.join(tmpdir, filepath)
    if not os.path.isdir(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    r = requests.get(url)
    with open(path, 'wb') as f:
        f.write(r.content)
    return path


# Download all files for the test
#     .
#     ├── img_dir
#     │   ├── img1.jpg
#     │   ├── img2.jpg
#     │   └── subdir
#     │       └── img3.jpg
#     ├── single_img.jpg
#     └── studio.json
tmpdir = tempfile.mkdtemp()
single_img_pth = download(tmpdir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/images/test.jpg', 'single_img.jpg')
img1_pth = download(tmpdir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/images/test.jpg', 'img_dir/img1.jpg')
img2_pth = download(tmpdir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/images/test.jpg', 'img_dir/img2.jpg')
img3_pth = download(tmpdir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/images/test.jpg', 'img_dir/subdir/img3.jpg')
json_pth = download(tmpdir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/json/studio.json', 'studio.json')
img_dir_pth = os.path.dirname(img1_pth)

def test_2e2_upload_single_image():
    run(['studio', 'add_images', '-d', 'deepocli-feedback-test-detection', '-o', 'travis-deepocli', single_img_pth])

def test_2e2_upload_image_dir():
    run(['studio', 'add_images', '-d', 'deepocli-feedback-test-detection', '-o', 'travis-deepocli', img_dir_pth])

def test_2e2_upload_image_dir_recursive():
    run(['studio', 'add_images', '-d', 'deepocli-feedback-test-detection', '-o', 'travis-deepocli', img_dir_pth, '--recursive'])

def test_2e2_upload_studio_json():
    run(['studio', 'add_images', '-d', 'deepocli-feedback-test-detection', '-o', 'travis-deepocli', json_pth, '--json'])
