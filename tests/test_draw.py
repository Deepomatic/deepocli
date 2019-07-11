import pytest
from utils import init_files_setup, run_cmd, OUTPUTS


# ------- Files setup ------------------------------------------------------------------------------------------------ #


# Retrieve INPUTS
INPUTS = init_files_setup()


def run_draw(*args, **kwargs):
    run_cmd(['draw'], *args, **kwargs)


# ------- Image Input Tests ------------------------------------------------------------------------------------------ #


@pytest.mark.parametrize(
    'outputs,expected',
    [
        ([OUTPUTS['IMAGE']], {'expect_nb_image': 1}),
        ([OUTPUTS['VIDEO']], {'expect_nb_video': 1}),
        ([OUTPUTS['STD']], {}),
        ([OUTPUTS['JSON']], {'expect_nb_json': 1}),
        ([OUTPUTS['DIR']], {'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 1}}}),
        (OUTPUTS['ALL'], {'expect_nb_json': 1, 'expect_nb_image': 1, 'expect_nb_video': 1, 'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 1}}})
    ]
)
def test_e2e_image_draw(outputs, expected):
    run_draw(INPUTS['IMAGE'], outputs, **expected)


# ------- Video Input Tests ------------------------------------------------------------------------------------------ #


@pytest.mark.parametrize(
    'outputs,expected',
    [
        ([OUTPUTS['IMAGE']], {'expect_nb_image': 21}),
        ([OUTPUTS['VIDEO']], {'expect_nb_video': 1}),
        ([OUTPUTS['STD']], {}),
        ([OUTPUTS['JSON']], {'expect_nb_json': 21}),
        ([OUTPUTS['DIR']], {'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 21}}}),
        (OUTPUTS['ALL'], {'expect_nb_json': 21, 'expect_nb_image': 21, 'expect_nb_video': 1, 'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 21}}})
    ]
)
def test_e2e_video_draw(outputs, expected):
    run_draw(INPUTS['VIDEO'], outputs, **expected)


# ------- Directory Input Tests -------------------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    'outputs,expected',
    [
        ([OUTPUTS['IMAGE']], {'expect_nb_image': 2}),
        ([OUTPUTS['VIDEO']], {'expect_nb_video': 1}),
        ([OUTPUTS['STD']], {}),
        ([OUTPUTS['JSON']], {'expect_nb_json': 2}),
        ([OUTPUTS['DIR']], {'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 2, 'expect_nb_subdir': 1}}}),
        (OUTPUTS['ALL'], {'expect_nb_json': 2, 'expect_nb_image': 2, 'expect_nb_video': 1, 'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 2, 'expect_nb_subdir': 1}}})
    ]
)
def test_e2e_directory_draw(outputs, expected):
    run_draw(INPUTS['DIRECTORY'], outputs, **expected)


# ------- Json Input Tests ------------------------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    'outputs,expected',
    [
        ([OUTPUTS['IMAGE']], {'expect_nb_image': 1}),
        ([OUTPUTS['VIDEO']], {'expect_nb_video': 1}),
        ([OUTPUTS['STD']], {}),
        ([OUTPUTS['JSON']], {'expect_nb_json': 1}),
        ([OUTPUTS['DIR']], {'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 1}}}),
        (OUTPUTS['ALL'], {'expect_nb_json': 1, 'expect_nb_image': 1, 'expect_nb_video': 1, 'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 1}}})
    ]
)
def test_e2e_json_draw(outputs, expected):
    run_draw(INPUTS['STUDIO_JSON'], outputs, **expected)


# ------- Special Options Tests -------------------------------------------------------------------------------------- #


def test_e2e_image_draw_image_verbose():
    run_draw(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1, extra_opts=['--verbose'])


def test_e2e_image_draw_image_threshold():
    run_draw(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1, extra_opts=['-t', '0.5'])


def test_e2e_video_draw_video_fps():
    run_draw(INPUTS['VIDEO'], [OUTPUTS['VIDEO']], expect_nb_video=1, extra_opts=['--output_fps', '2'])
    run_draw(INPUTS['VIDEO'], [OUTPUTS['VIDEO']], expect_nb_video=1, extra_opts=['--input_fps', '2'])


def test_e2e_image_draw_image_window():
    return  # window not handled by test
    # run_draw(INPUTS['IMAGE'], [OUTPUTS['WINDOW']], expect_nb_image=1, extra_opts=['--fullscreen'])


def test_e2e_image_draw_image_scores():
    run_draw(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1, extra_opts=['--draw_scores'])


def test_e2e_image_draw_image_labels():
    run_draw(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1, extra_opts=['--draw_labels'])


def test_e2e_image_draw_image_scores_and_labels():
    run_draw(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1, extra_opts=['--draw_scores', '--draw_labels'])


def test_e2e_image_draw_json_studio():
    run_draw(INPUTS['IMAGE'], [OUTPUTS['JSON']], expect_nb_json=1, studio_format=True, extra_opts=['--studio_format'])


def test_e2e_image_draw_from_file():
    run_draw(INPUTS['VIDEO'], [OUTPUTS['VIDEO']], expect_nb_video=1, extra_opts=['--from_file', INPUTS['OFFLINE_PRED']])
