import pytest
from utils import (init_files_setup, run_cmd, IMAGE_OUTPUT, VIDEO_OUTPUT,
                   STD_OUTPUT, JSON_OUTPUT, OUTPUTS, WINDOW_OUTPUT)


# ------- Files setup ------------------------------------------------------------------------------------------------ #

# Input to test: Image, Video, Directory, Json
IMAGE_INPUT, VIDEO_INPUT, DIRECTORY_INPUT, JSON_INPUT = init_files_setup()


def run_draw(*args, **kwargs):
    run_cmd(['draw'], *args, **kwargs)


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
def test_e2e_image_draw(outputs, expected):
    run_draw(IMAGE_INPUT, outputs, **expected)


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
def test_e2e_video_draw(outputs, expected):
    run_draw(VIDEO_INPUT, outputs, **expected)


# ------- Directory Input Tests -------------------------------------------------------------------------------------- #

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
def test_e2e_directory_draw(outputs, expected):
    run_draw(DIRECTORY_INPUT, outputs, **expected)


# ------- Json Input Tests ------------------------------------------------------------------------------------------- #


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
def test_e2e_json_draw(outputs, expected):
    run_draw(JSON_INPUT, outputs, **expected)


# ------- Special Options Tests -------------------------------------------------------------------------------------- #

def test_e2e_image_draw_image_threshold():
    run_draw(IMAGE_INPUT, [IMAGE_OUTPUT], expect_nb_image=1, extra_opts=['-t', '0.5'])


def test_e2e_video_draw_video_fps():
    run_draw(VIDEO_INPUT, [VIDEO_OUTPUT], expect_nb_video=1, extra_opts=['--output_fps', '2'])
    run_draw(VIDEO_INPUT, [VIDEO_OUTPUT], expect_nb_video=1, extra_opts=['--input_fps', '2'])


def test_e2e_image_draw_image_window():
    return  # window not handled by test
    run_draw(IMAGE_INPUT, [WINDOW_OUTPUT], expect_nb_image=1, extra_opts=['--fullscreen'])


def test_e2e_image_draw_image_scores():
    run_draw(IMAGE_INPUT, [IMAGE_OUTPUT], expect_nb_image=1, extra_opts=['--draw_scores'])


def test_e2e_image_draw_image_labels():
    run_draw(IMAGE_INPUT, [IMAGE_OUTPUT], expect_nb_image=1, extra_opts=['--draw_labels'])


def test_e2e_image_draw_image_scores_and_labels():
    run_draw(IMAGE_INPUT, [IMAGE_OUTPUT], expect_nb_image=1, extra_opts=['--draw_scores', '--draw_labels'])


def test_e2e_image_draw_json_studio():
    run_draw(IMAGE_INPUT, [JSON_OUTPUT], expect_nb_json=1, studio_format=True, extra_opts=['--studio_format'])
