# coding: utf-8
import os
import json
import shutil
import tempfile
import requests
from contextlib import contextmanager
from deepomatic.cli.cli_parser import run


# Define outputs
OUTPUTS = {
    'STD': 'stdout',
    'WINDOW': 'window',
    'IMAGE': 'image_output%04d.jpg',
    'VIDEO': 'video_output.mp4',
    'INT_WILDCARD_JSON': 'test_output%04d.json',
    'STR_WILDCARD_JSON': 'test_output%s.json',
    'NO_WILDCARD_JSON': 'test_output.json',
    'DIR': 'output_dir'
}
OUTPUTS['ALL'] = [output for output in list(OUTPUTS.values()) if output != 'window']


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
                    if isinstance(data, dict):
                        assert 'outputs' in data
                    elif isinstance(data, list):
                        assert len(data) == 0 or 'outputs' in data[0]
        elif path.endswith(('.jpg', '.jpeg')):
            nb_image += 1
        elif path.endswith('.mp4'):
            nb_video += 1
        elif os.path.isdir(os.path.join(directory, path)):
            nb_subdir += 1
    assert expect_nb_json == nb_json
    assert expect_nb_image == nb_image
    assert expect_nb_video == nb_video
    assert expect_nb_subdir == nb_subdir

    # Then check subdirectories
    if expect_subir:
        for path in os.listdir(directory):
            if os.path.isdir(path) and os.path.basename(os.path.normpath(path)) in expect_subir:
                check_directory(
                    path,
                    expect_nb_json=expect_subir[path].get('json', 0),
                    expect_nb_image=expect_subir[path].get('image', 0),
                    expect_nb_video=expect_subir[path].get('video', 0),
                    expect_nb_subdir=expect_subir[path].get('subdir', 0)
                )


def load_json_from_file(json_pth):
    """Load data from a json"""
    with open(json_pth, 'r') as json_file:
        json_data = json.load(json_file)
    return json_data


def load_studio_from_file(txt_path):
    """Load data from studio txt file"""
    ret = []
    with open(txt_path, 'r') as txt_file:
        for line in txt_file:
            ret.append(json.loads(line))
    return ret


def save_json_to_file(json_data, json_pth):
    """Save data to a json"""
    with open(json_pth, 'w') as json_file:
        json.dump(json_data, json_file)


def patch_json_for_tests(image_path, studio_json, vulcan_json):
    """Update the image path in test files"""
    # Patch vulcan JSON
    json_data = load_json_from_file(vulcan_json)
    json_data[0]['location'] = image_path
    save_json_to_file(json_data, vulcan_json)


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
    ├── single_img_corrupted.jpg
    ├── studio.json
    └── video.mp4
    """
    # Make temporary directory for file storage
    tmpdir = tempfile.mkdtemp()

    base_test_url = 'https://tests-resources.internal.deepomatic.com/deepocli/'

    # Download image and video files
    single_img_pth = download(tmpdir,
                              base_test_url + 'img.jpg',
                              'single_img.jpg')
    single_img_corrupted_pth = download(tmpdir,
                                        base_test_url + 'corrupted.jpg',
                                        'single_img_corrupted.jpg')
    video_pth = download(tmpdir, base_test_url + 'video.mp4', 'video.mp4')
    img_pth = download(tmpdir, base_test_url + 'img.jpg', 'img_dir/img1.jpg')
    download(tmpdir, base_test_url + 'img.jpg', 'img_dir/img2.jpg')
    download(tmpdir, base_test_url + 'img.jpg', 'img_dir/subdir/img3.jpg')

    unsupported_file = open(tmpdir + '/unsupported_data.abc', 'w')
    unsupported_file.close()
    

    # Download JSON files
    vulcan_json_pth = download(tmpdir, base_test_url + 'vulcan.json', 'vulcan.json')
    studio_json_pth = download(tmpdir, base_test_url + 'studio-views.txt', 'studio-views.txt')
    offline_pred_pth = download(tmpdir, base_test_url + 'offline_predictions.json',
                                'offline_predictions.json')
    img_dir_pth = os.path.dirname(img_pth)

    # Update json for path to match
    patch_json_for_tests(single_img_pth, studio_json_pth, vulcan_json_pth)

    # Build input dictionnary for easier handling
    INPUTS = {
        'IMAGE': single_img_pth,
        'IMAGE_CORRUPTED': single_img_corrupted_pth,
        'VIDEO': video_pth,
        'DIRECTORY': img_dir_pth,
        'STUDIO_JSON': studio_json_pth,
        'OFFLINE_PRED': offline_pred_pth,
        'VULCAN_JSON': vulcan_json_pth,
        'UNSUPPORTED_FILE': unsupported_file,
    }
    return INPUTS


def run_cmd(cmds, inp, outputs, *args, **kwargs):
    reco_opts = [] if 'noop' in cmds else ['-r', '44411']
    extra_opts = kwargs.pop('extra_opts', [])
    absolute_outputs = []
    with create_tmp_dir() as tmpdir:
        for output in outputs:
            if output in {OUTPUTS['STD'], OUTPUTS['WINDOW']}:
                absolute_outputs.append(output)
            elif output == OUTPUTS['DIR']:
                output_dir = os.path.join(tmpdir, OUTPUTS['DIR'])
                os.makedirs(output_dir)
                absolute_outputs.append(output_dir)
            else:
                absolute_outputs.append(os.path.join(tmpdir, output))
        run(cmds + ['-i', inp, '-o'] + absolute_outputs + reco_opts + extra_opts)
        check_directory(tmpdir, *args, **kwargs)


@contextmanager
def modified_environ(*remove, **update):
    """
    Temporarily updates the ``os.environ`` dictionary in-place.

    The ``os.environ`` dictionary is updated in-place so that the modification
    is sure to work in all situations.

    :param remove: Environment variables to remove.
    :param update: Dictionary of environment variables and values to add/update.

    Usage:
        a = os.environ.get('DEEPOMATIC_API_KEY')
        print(a)
        with modified_environ(DEEPOMATIC_API_KEY='24134'):
            a = os.environ.get('DEEPOMATIC_API_KEY')
            print(a)
    """
    env = os.environ
    update = update or {}
    remove = remove or []

    # List of environment variables being updated or removed.
    stomped = (set(update.keys()) | set(remove)) & set(env.keys())
    # Environment variables and values to restore on exit.
    update_after = {k: env[k] for k in stomped}
    # Environment variables and values to remove on exit.
    remove_after = frozenset(k for k in update if k not in env)

    try:
        env.update(update)
        [env.pop(k, None) for k in remove]
        yield
    finally:
        env.update(update_after)
        [env.pop(k) for k in remove_after]
