import pytest
from utils import (init_files_setup, run_cmd, IMAGE_OUTPUT, VIDEO_OUTPUT,
                   STD_OUTPUT, JSON_OUTPUT, OUTPUTS)


# ------- Files setup ------------------------------------------------------------------------------------------------ #

# Input to test: Image, Video, Directory, Json
IMAGE_INPUT, VIDEO_INPUT, DIRECTORY_INPUT, JSON_INPUT = init_files_setup()


def run_infer(*args, **kwargs):
    run_cmd(['infer'], *args, **kwargs)


# ------- Image Input Tests ------------------------------------------------------------------------------------------ #

@pytest.mark.parametrize(
    'outputs,expected',
    [
        ([IMAGE_OUTPUT], {'expect_nb_image': 1}),
        ([VIDEO_OUTPUT], {'expect_nb_video': 1}),
        ([STD_OUTPUT], {}),
        ([JSON_OUTPUT], {'expect_nb_json': 1}),
        (OUTPUTS, {'expect_nb_json': 1, 'expect_nb_image': 1, 'expect_nb_video': 1}),
    ]
)
def test_e2e_image_infer(outputs, expected):
    run_infer(IMAGE_INPUT, outputs, **expected)

# ------- Video Input Tests ------------------------------------------------------------------------------------------ #

@pytest.mark.parametrize(
    'outputs,expected',
    [
        ([IMAGE_OUTPUT], {'expect_nb_image': 21}),
        ([VIDEO_OUTPUT], {'expect_nb_video': 1}),
        ([STD_OUTPUT], {}),
        ([JSON_OUTPUT], {'expect_nb_json': 21}),
        (OUTPUTS, {'expect_nb_json': 21, 'expect_nb_image': 21, 'expect_nb_video': 1}),
    ]
)
def test_e2e_video_infer(outputs, expected):
    run_infer(VIDEO_INPUT, outputs, **expected)


# # ------- Directory Input Tests -------------------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    'outputs,expected',
    [
        ([IMAGE_OUTPUT], {'expect_nb_image': 2}),
        ([VIDEO_OUTPUT], {'expect_nb_video': 1}),
        ([STD_OUTPUT], {}),
        ([JSON_OUTPUT], {'expect_nb_json': 2}),
        (OUTPUTS, {'expect_nb_json': 2, 'expect_nb_image': 2, 'expect_nb_video': 1}),
    ]
)
def test_e2e_directory_infer(outputs, expected):
    run_infer(DIRECTORY_INPUT, outputs, **expected)


# # ------- Json Input Tests ------------------------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    'outputs,expected',
    [
        ([IMAGE_OUTPUT], {'expect_nb_image': 1}),
        ([VIDEO_OUTPUT], {'expect_nb_video': 1}),
        ([STD_OUTPUT], {}),
        ([JSON_OUTPUT], {'expect_nb_json': 1}),
        (OUTPUTS, {'expect_nb_json': 1, 'expect_nb_image': 1, 'expect_nb_video': 1}),
    ]
)
def test_e2e_json_infer(outputs, expected):
    run_infer(JSON_INPUT, outputs, **expected)


# # ------- Special Options Tests -------------------------------------------------------------------------------------- #


def test_e2e_image_infer_json_threshold():
    run_infer(IMAGE_INPUT, [JSON_OUTPUT], expect_nb_json=1, extra_opts=['-t', '0.5'])


def test_e2e_image_infer_json_studio():
    run_infer(IMAGE_INPUT, [JSON_OUTPUT], expect_nb_json=1, studio_format=True, extra_opts=['--studio-format'])
