import pytest
from utils import init_files_setup, run_cmd, OUTPUTS
from deepomatic.cli.common import SUPPORTED_FOURCC

# ------- Files setup ------------------------------------------------------------------------------------------------ #


# Retrieve INPUTS
INPUTS = init_files_setup()


def run_noop(*args, **kwargs):
    run_cmd(['platform', 'model', 'noop'], *args, **kwargs)


# ------- Image Input Tests ------------------------------------------------------------------------------------------ #


@pytest.mark.parametrize(
    'outputs,expected',
    [
        ([OUTPUTS['IMAGE']], {'expect_nb_image': 1}),
        ([OUTPUTS['VIDEO']], {'expect_nb_video': 1}),
        ([OUTPUTS['STD']], {}),
        ([OUTPUTS['DIR']], {'expect_nb_subdir': 1, 'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 1}}}),
    ]
)
def test_e2e_image_infer(outputs, expected, no_error_logs):
    run_noop(INPUTS['IMAGE'], outputs, **expected)


# ------- Video Input Tests ------------------------------------------------------------------------------------------ #


@pytest.mark.parametrize(
    'outputs,expected',
    [
        ([OUTPUTS['IMAGE']], {'expect_nb_image': 21}),
        ([OUTPUTS['VIDEO']], {'expect_nb_video': 1}),
        ([OUTPUTS['STD']], {}),
        ([OUTPUTS['DIR']], {'expect_nb_subdir': 1, 'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 21}}}),
    ]
)
def test_e2e_video_infer(outputs, expected, no_error_logs):
    run_noop(INPUTS['VIDEO'], outputs, **expected)


def test_e2e_video_noop_video_fourcc(no_error_logs):
    SKIP = ['avc1']
    for ext, supported_fourcc in SUPPORTED_FOURCC.items():
        output = 'VIDEO' + ext.upper().replace('.', '_')
        for fourcc in supported_fourcc:
            if fourcc not in SKIP:
                run_noop(INPUTS['VIDEO'], [OUTPUTS[output]], expect_nb_video=1, extra_opts=['--fourcc', fourcc])


# # ------- Directory Input Tests -------------------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    'outputs,expected',
    [
        ([OUTPUTS['IMAGE']], {'expect_nb_image': 2}),
        ([OUTPUTS['VIDEO']], {'expect_nb_video': 1}),
        ([OUTPUTS['STD']], {}),
        ([OUTPUTS['DIR']], {'expect_nb_subdir': 1, 'expect_subir': {OUTPUTS['DIR']: {'expect_nb_image': 2, 'expect_nb_subdir': 1}}}),
    ]
)
def test_e2e_directory_infer(outputs, expected, no_error_logs):
    run_noop(INPUTS['DIRECTORY'], outputs, **expected)
