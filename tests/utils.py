# coding: utf-8
import os
import json
import shutil
import tempfile
import requests
from contextlib import contextmanager
from deepomatic.cli.cli_parser import run


# Output to test: Image, Video, Stdout, Json
STD_OUTPUT = 'stdout'
WINDOW_OUTPUT = 'window'
IMAGE_OUTPUT = 'image_output%04d.jpg'
VIDEO_OUTPUT = 'video_output.mp4'
JSON_OUTPUT = 'test_output%04d.json'
DIR_OUTPUT = 'output_dir'
OUTPUTS = [STD_OUTPUT, IMAGE_OUTPUT, VIDEO_OUTPUT, JSON_OUTPUT, DIR_OUTPUT]


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
        shutil.rmtree(tmpdir)


def check_directory(directory,
                    expect_nb_json=0,
                    expect_nb_image=0,
                    expect_nb_video=0,
                    expect_nb_subdir=0,
                    studio_format=False,
                    expect_subir=None):
    # Start by checking main directory
    nb_json = 0
    nb_image = 0
    nb_video = 0
    nb_subdir = 0
    for path in os.listdir(directory):
        if path.endswith('.json'):
            nb_json += 1
            with open(os.path.join(directory, path)) as f:
                data = json.loads(f.read())
                if studio_format:
                    assert 'tags' in data
                    assert 'images' in data
                else:
                    assert 'outputs' in data
        elif path.endswith(('.jpg', '.jpeg')):
            nb_image += 1
        elif path.endswith('.mp4'):
            nb_video += 1
        elif os.path.isdir(path):
            nb_dir += 1
    assert expect_nb_json == nb_json
    assert expect_nb_image == nb_image
    assert expect_nb_video == nb_video
    assert expect_nb_subdir == nb_subdir

    # Then check subdirectories
    if expect_subir:
        for path in os.listdir(directory):
            if os.path.isdir(path):
                if os.path.basename(os.path.normpath(path)) in expect_subir:
                    check_directory(
                        path,
                        expect_nb_json=expect_subir[path].get('json', 0),
                        expect_nb_image=expect_subir[path].get('image', 0),
                        expect_nb_video=expect_subir[path].get('video', 0),
                        expect_nb_subdir=expect_subir[path].get('subdir', 0)
                    )


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
    single_img_pth = download(tmpdir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/images/test.jpg', 'single_img.jpg')
    video_pth = download(tmpdir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/videos/test.mp4', 'video.mp4')
    img1_pth = download(tmpdir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/images/test.jpg', 'img_dir/img1.jpg')
    img2_pth = download(tmpdir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/images/test.jpg', 'img_dir/img2.jpg')
    img3_pth = download(tmpdir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/images/test.jpg', 'img_dir/subdir/img3.jpg')
    json_pth = download(tmpdir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/json/studio.json', 'studio.json')
    offline_pred_pth = download(tmpdir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/json/offline_pred.json', 'offline_pred.json')
    img_dir_pth = os.path.dirname(img1_pth)

    # Update json for path to match
    with open(json_pth, 'r') as json_file:
        json_data = json.load(json_file)
    json_data['images'][0]['location'] = single_img_pth
    with open(json_pth, 'w') as json_file:
        json.dump(json_data, json_file)

    return single_img_pth, video_pth, img_dir_pth, json_pth, offline_pred_pth


def run_cmd(cmds, inp, outputs, *args, **kwargs):
    extra_opts = kwargs.pop('extra_opts', [])
    absolute_outputs = []
    with create_tmp_dir() as tmpdir:
        for output in outputs:
            if output in {STD_OUTPUT, WINDOW_OUTPUT}:
                absolute_outputs.append(output)
            elif output == DIR_OUTPUT:
                check_subdir = True
                output_dir = os.path.join(tmpdir, DIR_OUTPUT)
                os.makedirs(output_dir)
                absolute_outputs.append(output_dir)
            else:
                absolute_outputs.append(os.path.join(tmpdir, output))
        run(cmds + ['-i', inp, '-o'] + absolute_outputs + ['-r', 'fashion-v4'] + extra_opts)
        check_directory(tmpdir, *args, **kwargs)


if __name__ == '__main__':
    init_files_setup()
