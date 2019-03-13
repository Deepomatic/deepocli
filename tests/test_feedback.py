import os
from download_files import init_files_setup
from deepomatic.cli.cli_parser import run


# ------- Files setup ------------------------------------------------------------------------------------------------ #

# Input to test: Image, Directory, Json
image_input, video_input, directory_input, json_input, dir_output = init_files_setup()
TEST_DATASET = 'deepocli-feedback-test-detection'
TEST_ORG = 'travis-deepocli'


# ------- Studio Upload Tests----------------------------------------------------------------------------------------- #

def test_2e2_image_upload(test_input=image_input):
    run(['studio', 'add_images', '-d', TEST_DATASET, '-o', TEST_ORG, test_input])

def test_2e2_directory_upload(test_input=directory_input):
    run(['studio', 'add_images', '-d', TEST_DATASET, '-o', TEST_ORG, test_input])

def test_2e2_json_upload(test_input=json_input):
    run(['studio', 'add_images', '-d', TEST_DATASET, '-o', TEST_ORG, test_input, '--json'])


# ------- Special Options Tests -------------------------------------------------------------------------------------- #

def test_2e2_directory_upload_recursive(test_input=directory_input):
    run(['studio', 'add_images', '-d', TEST_DATASET, '-o', TEST_ORG, test_input, '--recursive'])
