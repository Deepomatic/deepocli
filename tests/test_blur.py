import pytest
from utils import init_files_setup, run_cmd, OUTPUTS


# ------- Files setup ------------------------------------------------------------------------------------------------ #


# Retrieve inputs
INPUTS = init_files_setup()


def run_blur(*args, **kwargs):
    run_cmd(['platform', 'model', 'blur'], *args, **kwargs)


# ------- Image Input Tests ------------------------------------------------------------------------------------------ #


@pytest.mark.parametrize(
    'outputs,expected',
    [
        ([OUTPUTS['IMAGE']], {'expect_nb_image': 1}),
        ([OUTPUTS['VIDEO']], {'expect_nb_video': 1}),
        ([OUTPUTS['STD']], {}),
        ([OUTPUTS['INT_WILDCARD_JSON']], {'expect_nb_json': 1}),
        ([OUTPUTS['STR_WILDCARD_JSON']], {'expect_nb_json': 1}),
        ([OUTPUTS['NO_WILDCARD_JSON']], {'expect_nb_json': 1}),
        ([OUTPUTS['DIR']], {'expect_nb_subdir': 1, 'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 1}}}),
        (OUTPUTS['ALL'], {
            'expect_nb_json': 3,
            'expect_nb_image': 1,
            'expect_nb_video': 1,
            'expect_nb_subdir': 1,
            'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 1}}
        })
    ]
)
def test_e2e_image_blur(outputs, expected, no_error_logs):
    run_blur(INPUTS['IMAGE'], outputs, **expected)


# ------- Video Input Tests ------------------------------------------------------------------------------------------ #


@pytest.mark.parametrize(
    'outputs,expected',
    [
        ([OUTPUTS['IMAGE']], {'expect_nb_image': 21}),
        ([OUTPUTS['VIDEO']], {'expect_nb_video': 1}),
        ([OUTPUTS['STD']], {}),
        ([OUTPUTS['INT_WILDCARD_JSON']], {'expect_nb_json': 21}),
        ([OUTPUTS['STR_WILDCARD_JSON']], {'expect_nb_json': 21}),
        ([OUTPUTS['NO_WILDCARD_JSON']], {'expect_nb_json': 1}),
        ([OUTPUTS['DIR']], {'expect_nb_subdir': 1, 'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 21}}}),
        (OUTPUTS['ALL'], {
            'expect_nb_json': 43,
            'expect_nb_image': 21,
            'expect_nb_video': 1,
            'expect_nb_subdir': 1,
            'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 21}}
        })
    ]
)
def test_e2e_video_blur(outputs, expected, no_error_logs):
    run_blur(INPUTS['VIDEO'], outputs, **expected)


# ------- Directory Input Tests -------------------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    'outputs,expected',
    [
        ([OUTPUTS['IMAGE']], {'expect_nb_image': 2}),
        ([OUTPUTS['VIDEO']], {'expect_nb_video': 1}),
        ([OUTPUTS['STD']], {}),
        ([OUTPUTS['INT_WILDCARD_JSON']], {'expect_nb_json': 2}),
        ([OUTPUTS['STR_WILDCARD_JSON']], {'expect_nb_json': 2}),
        ([OUTPUTS['NO_WILDCARD_JSON']], {'expect_nb_json': 1}),
        ([OUTPUTS['DIR']], {'expect_nb_subdir': 1, 'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 2, 'expect_nb_subdir': 1}}}),
        (OUTPUTS['ALL'], {
            'expect_nb_json': 5,
            'expect_nb_image': 2,
            'expect_nb_video': 1,
            'expect_nb_subdir': 1,
            'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 2, 'expect_nb_subdir': 1}}
        })
    ]
)
def test_e2e_directory_blur(outputs, expected, no_error_logs):
    run_blur(INPUTS['DIRECTORY'], outputs, **expected)


# # ------- Special Options Tests -------------------------------------------------------------------------------------- #


def test_e2e_image_blur_image_verbose(no_error_logs):
    run_blur(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1,
             extra_opts=['--verbose'])


def test_e2e_image_blur_image_threshold(no_error_logs):
    run_blur(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1,
             extra_opts=['-t', '0.5'])


def test_e2e_video_blur_video_fps(no_error_logs):
    run_blur(INPUTS['VIDEO'], [OUTPUTS['VIDEO']], expect_nb_video=1,
             extra_opts=['--output_fps', '2'])
    run_blur(INPUTS['VIDEO'], [OUTPUTS['VIDEO']], expect_nb_video=1,
             extra_opts=['--input_fps', '2'])


@pytest.mark.skip(reason="window not handled by test")
def test_e2e_image_blur_image_window(no_error_logs):
    run_blur(INPUTS['IMAGE'], [OUTPUTS['WINDOW']], expect_nb_image=1,
             extra_opts=['--fullscreen'])


def test_e2e_image_blur_image_method(no_error_logs):
    run_blur(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1,
             extra_opts=['--blur_method', 'pixel'])


def test_e2e_image_blur_image_strengh(no_error_logs):
    run_blur(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1,
             extra_opts=['--blur_strength', '5'])


def test_e2e_image_blur_image_method_and_strength(no_error_logs):
    run_blur(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1,
             extra_opts=['--blur_method', 'pixel', '--blur_strength', '5'])


def test_e2e_image_blur_from_file(no_error_logs):
    run_blur(INPUTS['VIDEO'], [OUTPUTS['VIDEO']], expect_nb_video=1,
             extra_opts=['--from_file', INPUTS['OFFLINE_PRED']])


def test_e2e_image_corrupted_blur_image():
    run_blur(INPUTS['IMAGE_CORRUPTED'], [OUTPUTS['IMAGE']], expect_nb_image=0)
