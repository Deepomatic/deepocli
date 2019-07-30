import pytest
from utils import init_files_setup, run_cmd, OUTPUTS


# ------- Files setup ------------------------------------------------------------------------------------------------ #


# Retrieve inputs
INPUTS = init_files_setup()


def run_blur(*args, **kwargs):
    run_cmd(['blur'], *args, **kwargs)


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
        ([OUTPUTS['DIR']], {'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 1}}}),
        (OUTPUTS['ALL'], {'expect_nb_json': 3, 'expect_nb_image': 1, 'expect_nb_video': 1, 'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 1}}})
    ]
)
def test_e2e_image_blur(outputs, expected):
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
        ([OUTPUTS['DIR']], {'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 21}}}),
        (OUTPUTS['ALL'], {'expect_nb_json': 43, 'expect_nb_image': 21, 'expect_nb_video': 1, 'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 21}}})
    ]
)
def test_e2e_video_blur(outputs, expected):
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
        ([OUTPUTS['DIR']], {'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 2, 'expect_nb_subdir': 1}}}),
        (OUTPUTS['ALL'], {'expect_nb_json': 5, 'expect_nb_image': 2, 'expect_nb_video': 1, 'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 2, 'expect_nb_subdir': 1}}})
    ]
)
def test_e2e_directory_blur(outputs, expected):
    run_blur(INPUTS['DIRECTORY'], outputs, **expected)


# ------- Json Input Tests ------------------------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    'outputs,expected',
    [
        ([OUTPUTS['IMAGE']], {'expect_nb_image': 1}),
        ([OUTPUTS['VIDEO']], {'expect_nb_video': 1}),
        ([OUTPUTS['STD']], {}),
        ([OUTPUTS['INT_WILDCARD_JSON']], {'expect_nb_json': 1}),
        ([OUTPUTS['STR_WILDCARD_JSON']], {'expect_nb_json': 1}),
        ([OUTPUTS['NO_WILDCARD_JSON']], {'expect_nb_json': 1}),
        ([OUTPUTS['DIR']], {'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 1}}}),
        (OUTPUTS['ALL'], {'expect_nb_json': 3, 'expect_nb_image': 1, 'expect_nb_video': 1, 'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 1}}})
    ]
)
def test_e2e_json_blur(outputs, expected):
    run_blur(INPUTS['STUDIO_JSON'], outputs, **expected)


# # ------- Special Options Tests -------------------------------------------------------------------------------------- #


def test_e2e_image_blur_image_verbose():
    run_blur(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1, extra_opts=['--verbose'])


def test_e2e_image_blur_image_threshold():
    run_blur(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1, extra_opts=['-t', '0.5'])


def test_e2e_video_blur_video_fps():
    run_blur(INPUTS['VIDEO'], [OUTPUTS['VIDEO']], expect_nb_video=1, extra_opts=['--output_fps', '2'])
    run_blur(INPUTS['VIDEO'], [OUTPUTS['VIDEO']], expect_nb_video=1, extra_opts=['--input_fps', '2'])


@pytest.mark.skip(reason="window not handled by test")
def test_e2e_image_blur_image_window():
    run_blur(INPUTS['IMAGE'], [OUTPUTS['WINDOW']], expect_nb_image=1, extra_opts=['--fullscreen'])


def test_e2e_image_blur_image_method():
    run_blur(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1, extra_opts=['--blur_method', 'pixel'])


def test_e2e_image_blur_image_strengh():
    run_blur(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1, extra_opts=['--blur_strength', '5'])


def test_e2e_image_blur_image_method_and_strenght():
    run_blur(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1, extra_opts=['--blur_method', 'pixel', '--blur_strength', '5'])


def test_e2e_image_blur_json_studio():
    run_blur(INPUTS['IMAGE'], [OUTPUTS['NO_WILDCARD_JSON']], expect_nb_json=1, studio_format=True, extra_opts=['--studio_format'])


def test_e2e_image_blur_from_file():
    run_blur(INPUTS['VIDEO'], [OUTPUTS['VIDEO']], expect_nb_video=1, extra_opts=['--from_file', INPUTS['OFFLINE_PRED']])
