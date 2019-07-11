from deepomatic.cli.cli_parser import run
from utils import init_files_setup


# ------- Files setup ------------------------------------------------------------------------------------------------ #


# Retrieve INPUTS
INPUTS = init_files_setup()
TEST_DATASET = 'deepocli-feedback-test-detection'
TEST_ORG = 'travis-deepocli'


def run_add_images(test_input, extra_opts=None):
    extra_opts = extra_opts or []
    run(['studio', 'add_images', '-d', TEST_DATASET, '-o', TEST_ORG, test_input] + extra_opts)


# ------- Studio Upload Tests----------------------------------------------------------------------------------------- #


def test_2e2_image_upload():
    run_add_images(INPUTS['IMAGE'])


def test_2e2_directory_upload():
    run_add_images(INPUTS['DIRECTORY'])


def test_2e2_vulcan_json_upload():
    run_add_images(INPUTS['VULCAN_JSON'], extra_opts=['--json'])


def test_2e2_studio_json_upload():
    run_add_images(INPUTS['STUDIO_JSON'], extra_opts=['--json'])


def test_2e2_single_object_studio_json_upload():
    run_add_images(INPUTS['SINGLE_OBJECT_STUDIO_JSON'], extra_opts=['--json'])


# ------- Special Options Tests -------------------------------------------------------------------------------------- #


def test_2e2_directory_upload_verbose():
    run_add_images(INPUTS['DIRECTORY'], extra_opts=['--verbose'])


def test_2e2_directory_upload_recursive():
    run_add_images(INPUTS['DIRECTORY'], extra_opts=['--recursive'])
