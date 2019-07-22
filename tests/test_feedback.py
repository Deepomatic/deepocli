from deepomatic.cli.cli_parser import run
from utils import init_files_setup


# ------- Files setup ------------------------------------------------------------------------------------------------ #


# Input to test: Image, Directory, Json
IMAGE_INPUT, VIDEO_INPUT, DIRECTORY_INPUT, JSON_INPUT, _ = init_files_setup()
TEST_DATASET = 'deepocli-feedback-test-detection'
TEST_ORG = 'travis-deepocli'


def run_add_images(test_input, extra_opts=None):
    extra_opts = extra_opts or []
    run(['studio', 'add_images', '-d', TEST_DATASET, '-o', TEST_ORG, '-i', test_input] + extra_opts)


# ------- Studio Upload Tests----------------------------------------------------------------------------------------- #


def test_2e2_image_upload():
    run_add_images(IMAGE_INPUT)


def test_2e2_directory_upload():
    run_add_images(DIRECTORY_INPUT)


def test_2e2_json_upload():
    run_add_images(JSON_INPUT, extra_opts=['--json'])


# ------- Special Options Tests -------------------------------------------------------------------------------------- #


def test_2e2_directory_upload_verbose():
    run_add_images(DIRECTORY_INPUT, extra_opts=['--verbose'])


def test_2e2_directory_upload_recursive():
    run_add_images(DIRECTORY_INPUT, extra_opts=['--recursive'])
