import glob
import pytest
from PIL import Image
from utils import init_files_setup, run_cmd, ctx_run_cmd, OUTPUTS


# ------- Files setup ------------------------------------------------------------------------------------------------ #


# Retrieve INPUTS
INPUTS = init_files_setup()
CMD_PREFIX = ['platform', 'model', 'infer']


def run_infer(*args, **kwargs):
    run_cmd(CMD_PREFIX, *args, **kwargs)


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
        ([OUTPUTS['JSONL']], {'expect_nb_jsonl': 1}),
        ([OUTPUTS['DIR']], {'expect_nb_subdir': 1, 'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 1}}}),
        (OUTPUTS['ALL'], {
            'expect_nb_json': 3,
            'expect_nb_jsonl': 1,
            'expect_nb_image': 1,
            'expect_nb_video': 2,
            'expect_nb_subdir': 1,
            'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 1}}
        })
    ]
)
def test_e2e_image_infer(outputs, expected, no_error_logs):
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
        ([OUTPUTS['JSONL']], {'expect_nb_jsonl': 1}),
        ([OUTPUTS['DIR']], {'expect_nb_subdir': 1, 'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 21}}}),
        (OUTPUTS['ALL'], {
            'expect_nb_json': 43,
            'expect_nb_jsonl': 1,
            'expect_nb_image': 21,
            'expect_nb_video': 2,
            'expect_nb_subdir': 1,
            'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 21}}
        })
    ]
)
def test_e2e_video_infer(outputs, expected, no_error_logs):
    run_infer(INPUTS['VIDEO'], outputs, **expected)


def test_e2e_video_infer_color_space(no_error_logs):
    with ctx_run_cmd(CMD_PREFIX, INPUTS['VIDEO'], [OUTPUTS['IMAGE']],
                     extra_opts=['--output_color_space', 'GRAY'], expect_nb_image=21) as tmpdir:
        images = glob.glob('{}/*.jpg'.format(tmpdir))
        image = Image.open(images[0])
        assert image.mode == 'L'


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
        ([OUTPUTS['JSONL']], {'expect_nb_jsonl': 1}),
        ([OUTPUTS['DIR']], {'expect_nb_subdir': 1, 'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 2, 'expect_nb_subdir': 1}}}),
        (OUTPUTS['ALL'], {
            'expect_nb_json': 5,
            'expect_nb_jsonl': 1,
            'expect_nb_image': 2,
            'expect_nb_video': 2,
            'expect_nb_subdir': 1,
            'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 2, 'expect_nb_subdir': 1}}
        })
    ]
)
def test_e2e_directory_infer(outputs, expected, no_error_logs):
    run_infer(INPUTS['DIRECTORY'], outputs, **expected)


# # ------- Studio Input Tests -------------------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    'outputs,expected',
    [
        ([OUTPUTS['IMAGE']], {'expect_nb_image': 1}),
        ([OUTPUTS['VIDEO']], {'expect_nb_video': 1}),
        ([OUTPUTS['STD']], {}),
        ([OUTPUTS['DIR']], {'expect_nb_subdir': 1, 'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 2, 'expect_nb_subdir': 1}}}),
    ]
)
def test_e2e_studio_infer(outputs, expected, no_error_logs):
    run_infer(INPUTS['STUDIO_JSON'], outputs, **expected)


# # ------- Special Options Tests -------------------------------------------------------------------------------------- #


def test_e2e_image_infer_json_verbose(no_error_logs):
    run_infer(INPUTS['IMAGE'], [OUTPUTS['NO_WILDCARD_JSON']], expect_nb_json=1,
              extra_opts=['--verbose'])


def test_e2e_image_infer_json_threshold(no_error_logs):
    run_infer(INPUTS['IMAGE'], [OUTPUTS['NO_WILDCARD_JSON']], expect_nb_json=1,
              extra_opts=['-t', '0.5'])


def test_e2e_image_corrupted_infer_json():
    run_infer(INPUTS['IMAGE_CORRUPTED'], [OUTPUTS['INT_WILDCARD_JSON']],
              expect_nb_json=0)


def test_e2e_image_infer_reproduce_input_dir_struct(no_error_logs):
    run_infer(INPUTS['DIRECTORY'], [OUTPUTS['STR_WILDCARD_JSON']], expect_nb_json=2,
              expect_nb_subdir=1, extra_opts=['--recursive'])
