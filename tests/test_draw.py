import os
from download_files import init_files_setup
from deepomatic.cli.cli_parser import run


# ------- Files setup ------------------------------------------------------------------------------------------------ #

# Input to test: Image, Video, Directory, Json
image_input, video_input, directory_input, json_input, dir_output = init_files_setup()
# Output to test: Image, Video, Stdout, Json, Directory
std_output = 'stdout'
image_output = os.path.join(dir_output, 'image_output%4d.jpg')
video_output = os.path.join(dir_output, 'video_output%4d.mp4')
json_output = os.path.join(dir_output, 'test_output%4d.json')
directory_output = dir_output
outputs = [std_output, image_output, video_output, json_output, directory_output]

# ------- Image Input Tests ------------------------------------------------------------------------------------------ #


def test_e2e_image_draw_image(test_input=image_input, test_output=image_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_image_draw_video(test_input=image_input, test_output=video_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_image_draw_stdout(test_input=image_input, test_output=std_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_image_draw_json(test_input=image_input, test_output=json_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_image_draw_directory(test_input=image_input, test_output=directory_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_image_draw_multiples(test_input=image_input, test_output=outputs):
    run(['draw', '-i', test_input, '-o'] + outputs + ['-r', 'fashion-v4'])


# ------- Video Input Tests ------------------------------------------------------------------------------------------ #


def test_e2e_video_draw_image(test_input=video_input, test_output=image_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_video_draw_video(test_input=video_input, test_output=video_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_video_draw_stdout(test_input=video_input, test_output=std_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_video_draw_json(test_input=video_input, test_output=json_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_video_draw_directory(test_input=video_input, test_output=directory_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_video_draw_multiples(test_input=video_input, test_output=outputs):
    run(['draw', '-i', test_input, '-o'] + outputs + ['-r', 'fashion-v4'])


# ------- Directory Input Tests -------------------------------------------------------------------------------------- #


def test_e2e_directory_draw_image(test_input=directory_input, test_output=image_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_directory_draw_video(test_input=directory_input, test_output=video_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_directory_draw_stdout(test_input=directory_input, test_output=std_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_directory_draw_json(test_input=directory_input, test_output=json_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_directory_draw_directory(test_input=directory_input, test_output=directory_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_directory_draw_multiples(test_input=directory_input, test_output=outputs):
    run(['draw', '-i', test_input, '-o'] + outputs + ['-r', 'fashion-v4'])


# ------- Json Input Tests ------------------------------------------------------------------------------------------- #


def test_e2e_json_draw_image(test_input=json_input, test_output=image_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_json_draw_video(test_input=json_input, test_output=video_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_json_draw_stdout(test_input=json_input, test_output=std_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_json_draw_json(test_input=json_input, test_output=json_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_json_draw_directory(test_input=json_input, test_output=directory_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_json_draw_multiples(test_input=json_input, test_output=outputs):
    run(['draw', '-i', test_input, '-o'] + outputs + ['-r', 'fashion-v4'])



# ------- Special Options Tests -------------------------------------------------------------------------------------- #

def test_e2e_image_draw_image_threshold(test_input=image_input, test_output=image_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4', '-t', '0.5'])


def test_e2e_video_draw_video_fps(test_input=video_input, test_output=video_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4', '--fps', '2'])


def test_e2e_image_draw_image_window(test_input=image_input, test_output='window'):
    return  # window not handled by test
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4', '--fullscreen'])


def test_e2e_image_draw_image_scores(test_input=image_input, test_output=image_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4', '--draw_scores'])


def test_e2e_image_draw_image_labels(test_input=image_input, test_output=image_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4', '--draw_labels'])


def test_e2e_image_draw_image_scores_and_labels(test_input=image_input, test_output=image_output):
    run(['draw', '-i', test_input, '-o', test_output, '-r', 'fashion-v4', '--draw_scores', '--draw_labels'])
