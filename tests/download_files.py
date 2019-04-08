# coding: utf-8
import os
import json
import shutil
import tempfile
import requests
from contextlib import contextmanager


def download(tmpdir, url, filepath):
    path = os.path.join(tmpdir, filepath)
    if not os.path.isdir(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    r = requests.get(url)
    if r.status_code != 200:
        raise ValueError('Status {} for URL {}'.format(r.status_code, url))
    else:
        with open(path, 'wb') as f:
            f.write(r.content)
        return path


@contextmanager
def create_tmp_dir():
    tmpdir = tempfile.mkdtemp()
    try:
        yield tmpdir
    finally:
        # shutil.rmtree(tmpdir)
        pass


def check_directory(directory,
                    expect_nb_json=0,
                    expect_nb_image=0,
                    expect_nb_video=0,
                    studio_format=False):
    nb_json = 0
    nb_image = 0
    nb_video = 0
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            nb_json += 1
            with open(os.path.join(directory, filename)) as f:
                data = json.loads(f.read())
                if studio_format:
                    assert 'tags' in data
                    assert 'images' in data
                else:
                    assert 'outputs' in data
        elif filename.endswith(('.jpg', '.jpeg')):
            nb_image += 1
        elif filename.endswith('.mp4'):
            nb_video += 1
    assert expect_nb_json == nb_json
    assert expect_nb_image == nb_image
    assert expect_nb_video == nb_video


def init_files_setup():
    """
    Download all files for the tests. The files structure is the following

    tmpdir
    ├── img_dir
    │   ├── img1.jpg
    │   ├── img2.jpg
    │   └── subdir
    │       └── img3.jpg
    ├── single_img.jpg
    ├── studio.json
    └── video.mp4
    """
    # Download all fies
    tmpdir = tempfile.mkdtemp()
    inputs_dir = os.path.join(tmpdir, 'inputs')
    os.makedirs(inputs_dir)
    outputs_dir = os.path.join(tmpdir, 'outputs')
    os.makedirs(outputs_dir)
    single_img_pth = download(inputs_dir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/images/test.jpg', 'single_img.jpg')
    video_pth = download(inputs_dir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/videos/test.mp4', 'video.mp4')
    img1_pth = download(inputs_dir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/images/test.jpg', 'img_dir/img1.jpg')
    img2_pth = download(inputs_dir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/images/test.jpg', 'img_dir/img2.jpg')
    img3_pth = download(inputs_dir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/images/test.jpg', 'img_dir/subdir/img3.jpg')
    json_pth = download(inputs_dir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/json/studio.json', 'studio.json')
    img_dir_pth = os.path.dirname(img1_pth)

    # Update json for path to match
    with open(json_pth, 'r') as json_file:
        json_data = json.load(json_file)
    json_data['images'][0]['location'] = single_img_pth
    with open(json_pth, 'w') as json_file:
        json.dump(json_data, json_file)

    return single_img_pth, video_pth, img_dir_pth, json_pth, outputs_dir


if __name__ == '__main__':
    init_files_setup()
