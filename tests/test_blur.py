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
outputs = [std_output, image_output, video_output, json_output]


# ------- Image Input Tests ------------------------------------------------------------------------------------------ #


def test_e2e_image_blur_image(test_input=image_input, test_output=image_output):
    run(['blur', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_image_blur_video(test_input=image_input, test_output=video_output):
    run(['blur', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_image_blur_stdout(test_input=image_input, test_output=std_output):
    run(['blur', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_image_blur_json(test_input=image_input, test_output=json_output):
    run(['blur', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_image_blur_multiples(test_input=image_input, test_output=outputs):
    run(['blur', '-i', test_input, '-o'] + outputs + ['-r', 'fashion-v4'])


# ------- Video Input Tests ------------------------------------------------------------------------------------------ #


def test_e2e_video_blur_image(test_input=video_input, test_output=image_output):
    run(['blur', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_video_blur_video(test_input=video_input, test_output=video_output):
    run(['blur', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_video_blur_stdout(test_input=video_input, test_output=std_output):
    run(['blur', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_video_blur_json(test_input=video_input, test_output=json_output):
    run(['blur', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_video_blur_multiples(test_input=video_input, test_output=outputs):
    run(['blur', '-i', test_input, '-o'] + outputs + ['-r', 'fashion-v4'])


# # ------- Directory Input Tests -------------------------------------------------------------------------------------- #


def test_e2e_directory_blur_image(test_input=directory_input, test_output=image_output):
    run(['blur', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_directory_blur_video(test_input=directory_input, test_output=video_output):
    run(['blur', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_directory_blur_stdout(test_input=directory_input, test_output=std_output):
    run(['blur', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_directory_blur_json(test_input=directory_input, test_output=json_output):
    run(['blur', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_directory_blur_multiples(test_input=directory_input, test_output=outputs):
    run(['blur', '-i', test_input, '-o'] + outputs + ['-r', 'fashion-v4'])


# # ------- Json Input Tests ------------------------------------------------------------------------------------------- #


def test_e2e_json_blur_image(test_input=json_input, test_output=image_output):
    run(['blur', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_json_blur_video(test_input=json_input, test_output=video_output):
    run(['blur', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_json_blur_stdout(test_input=json_input, test_output=std_output):
    run(['blur', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_json_blur_json(test_input=json_input, test_output=json_output):
    run(['blur', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


def test_e2e_json_blur_multiples(test_input=json_input, test_output=outputs):
    run(['blur', '-i', test_input, '-o'] + outputs + ['-r', 'fashion-v4'])


# # ------- Special Options Tests -------------------------------------------------------------------------------------- #


def test_e2e_image_blur_image_threshold(test_input=image_input, test_output=image_output):
    run(['blur', '-i', test_input, '-o', test_output, '-r', 'fashion-v4', '-t', '0.5'])


def test_e2e_video_blur_video_fps(test_input=video_input, test_output=video_output):
    run(['blur', '-i', test_input, '-o', test_output, '-r', 'fashion-v4', '--fps', '2'])


def test_e2e_image_blur_image_window(test_input=image_input, test_output='window'):
    return  # window not handled by test
    run(['blur', '-i', test_input, '-o', test_output, '-r', 'fashion-v4', '--fullscreen'])


def test_e2e_image_blur_image_method(test_input=image_input, test_output=image_output):
    run(['blur', '-i', test_input, '-o', test_output, '-r', 'fashion-v4', '--blur_method', 'pixel'])


def test_e2e_image_blur_image_strengh(test_input=image_input, test_output=image_output):
    run(['blur', '-i', test_input, '-o', test_output, '-r', 'fashion-v4', '--blur_strength', '5'])


def test_e2e_image_blur_image_method_and_strenght(test_input=image_input, test_output=image_output):
    run(['blur', '-i', test_input, '-o', test_output, '-r', 'fashion-v4', '--blur_method', 'pixel', '--blur_strength', '5'])
