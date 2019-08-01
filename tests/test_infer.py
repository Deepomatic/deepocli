import pytest
from utils import init_files_setup, run_cmd, OUTPUTS


# ------- Files setup ------------------------------------------------------------------------------------------------ #


# Retrieve INPUTS
INPUTS = init_files_setup()


def run_infer(*args, **kwargs):
    run_cmd(['infer'], *args, **kwargs)


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
def test_e2e_image_infer(outputs, expected):
    run_infer(INPUTS['IMAGE'], outputs, **expected)


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
def test_e2e_video_infer(outputs, expected):
    run_infer(INPUTS['VIDEO'], outputs, **expected)


# # ------- Directory Input Tests -------------------------------------------------------------------------------------- #


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
def test_e2e_directory_infer(outputs, expected):
    run_infer(INPUTS['DIRECTORY'], outputs, **expected)


# # ------- Json Input Tests ------------------------------------------------------------------------------------------- #


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
def test_e2e_json_infer(outputs, expected):
    run_infer(INPUTS['STUDIO_JSON'], outputs, **expected)


# # ------- Special Options Tests -------------------------------------------------------------------------------------- #


def test_e2e_image_infer_json_verbose():
    run_infer(INPUTS['IMAGE'], [OUTPUTS['NO_WILDCARD_JSON']], expect_nb_json=1, extra_opts=['--verbose'])


def test_e2e_image_infer_json_threshold():
    run_infer(INPUTS['IMAGE'], [OUTPUTS['NO_WILDCARD_JSON']], expect_nb_json=1, extra_opts=['-t', '0.5'])


def test_e2e_image_infer_json_studio():
    run_infer(INPUTS['IMAGE'], [OUTPUTS['NO_WILDCARD_JSON']], expect_nb_json=1, studio_format=True, extra_opts=['--studio_format'])


def test_e2e_image_corrupted_infer_json():
    run_infer(INPUTS['IMAGE_CORRUPTED'], [OUTPUTS['NO_WILDCARD_JSON']], expect_nb_json=0)
