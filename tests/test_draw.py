import pytest
from utils import init_files_setup, run_cmd, OUTPUTS
from deepomatic.cli.common import SUPPORTED_FOURCC

# ------- Files setup ------------------------------------------------------------------------------------------------ #


# Retrieve INPUTS
INPUTS = init_files_setup()


def run_draw(*args, **kwargs):
    run_cmd(['platform', 'model', 'draw'], *args, **kwargs)


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
def test_e2e_image_draw(outputs, expected, no_error_logs):
    run_draw(INPUTS['IMAGE'], outputs, **expected)


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
def test_e2e_video_draw(outputs, expected, no_error_logs):
    run_draw(INPUTS['VIDEO'], outputs, **expected)


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
def test_e2e_directory_draw(outputs, expected, no_error_logs):
    run_draw(INPUTS['DIRECTORY'], outputs, **expected)


# ------- Special Options Tests -------------------------------------------------------------------------------------- #


def test_e2e_image_draw_image_verbose(no_error_logs):
    run_draw(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1,
             extra_opts=['--verbose'])


def test_e2e_image_draw_image_threshold(no_error_logs):
    run_draw(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1,
             extra_opts=['-t', '0.5'])


def test_e2e_video_draw_video_fps(no_error_logs):
    run_draw(INPUTS['VIDEO'], [OUTPUTS['VIDEO']], expect_nb_video=1, extra_opts=['--output_fps', '2'])
    run_draw(INPUTS['VIDEO'], [OUTPUTS['VIDEO']], expect_nb_video=1, extra_opts=['--input_fps', '2'])


def test_e2e_video_draw_video_fourcc(no_error_logs):
    for ext, supported_fourcc in SUPPORTED_FOURCC.items():
        output = 'VIDEO' + ext.upper().replace('.', '_')
        for fourcc in supported_fourcc:
            run_draw(INPUTS['VIDEO'], [output], expect_nb_video=1, extra_opts=['--fourcc', fourcc])


@pytest.mark.skip(reason="window not handled by test")
def test_e2e_image_draw_image_window(no_error_logs):
    run_draw(INPUTS['IMAGE'], [OUTPUTS['WINDOW']], expect_nb_image=1,
             extra_opts=['--fullscreen'])


def test_e2e_image_draw_image_scores(no_error_logs):
    run_draw(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1,
             extra_opts=['--draw_scores'])


def test_e2e_image_draw_image_no_scores(no_error_logs):
    run_draw(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1,
             extra_opts=['--no_draw_scores'])


def test_e2e_image_draw_image_labels(no_error_logs):
    run_draw(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1,
             extra_opts=['--draw_labels'])


def test_e2e_image_draw_image_no_labels(no_error_logs):
    run_draw(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1,
             extra_opts=['--no_draw_labels'])


def test_e2e_image_draw_image_scores_and_labels(no_error_logs):
    run_draw(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1,
             extra_opts=['--draw_scores', '--draw_labels'])


def test_e2e_image_draw_image_no_scores_and_no_labels(no_error_logs):
    run_draw(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1,
             extra_opts=['--no_draw_scores', '--no_draw_labels'])


def test_e2e_image_draw_image_font_scale_and_thickness(no_error_logs):
    run_draw(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1,
             extra_opts=['-fs', '2'])
    run_draw(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1,
             extra_opts=['-ft', '2'])


def test_e2e_image_draw_image_font_bg_color(no_error_logs):
    run_draw(INPUTS['IMAGE'], [OUTPUTS['IMAGE']], expect_nb_image=1,
             extra_opts=['--font_bg_color', '255', '0', '0'])


def test_e2e_image_draw_from_file(no_error_logs):
    run_draw(INPUTS['VIDEO'], [OUTPUTS['VIDEO']], expect_nb_video=1,
             extra_opts=['--from_file', INPUTS['OFFLINE_PRED']])


def test_e2e_image_corrupted_draw_image():
    run_draw(INPUTS['IMAGE_CORRUPTED'], [OUTPUTS['IMAGE']], expect_nb_image=0)
