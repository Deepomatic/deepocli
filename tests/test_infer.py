import os
from download_files import init_files_setup
from deepomatic.cli.cli_parser import run


# ------- Files setup ------------------------------------------------------------------------------------------------ #

# Input to test: Image, Video, Directory, Json
image_input, video_input, directory_input, json_input, dir_output = init_files_setup()
# Output to test: Stdout, Json, Directory
std_output = 'stdout'
json_output = os.path.join(dir_output, 'test_output%4d.json')
directory_output = dir_output


# ------- Image Input Tests ------------------------------------------------------------------------------------------ #

def test_e2e_image_infer_stdout(test_input=image_input, test_output=std_output):
    run(['infer', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])

def test_e2e_image_infer_json(test_input=image_input, test_output=json_output):
    run(['infer', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])

def test_e2e_image_infer_directory(test_input=image_input, test_output=directory_output):
    run(['infer', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


# ------- Video Input Tests ------------------------------------------------------------------------------------------ #

def test_e2e_video_infer_stdout(test_input=video_input, test_output=std_output):
    run(['infer', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])

def test_e2e_video_infer_json(test_input=video_input, test_output=json_output):
    run(['infer', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])

def test_e2e_video_infer_directory(test_input=video_input, test_output=directory_output):
    run(['infer', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


# ------- Directory Input Tests -------------------------------------------------------------------------------------- #

def test_e2e_directory_infer_stdout(test_input=directory_input, test_output=std_output):
    run(['infer', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])

def test_e2e_directory_infer_json(test_input=directory_input, test_output=json_output):
    run(['infer', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])

def test_e2e_directory_infer_directory(test_input=directory_input, test_output=directory_output):
    run(['infer', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


# ------- Json Input Tests ------------------------------------------------------------------------------------------- #

def test_e2e_json_infer_stdout(test_input=json_input, test_output=std_output):
    run(['infer', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])

def test_e2e_json_infer_json(test_input=json_input, test_output=json_output):
    run(['infer', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])

def test_e2e_json_infer_directory(test_input=json_input, test_output=directory_output):
    run(['infer', '-i', test_input, '-o', test_output, '-r', 'fashion-v4'])


# ------- Special Options Tests -------------------------------------------------------------------------------------- #

def test_e2e_image_infer_json_threshold(test_input=image_input, test_output=json_output):
    run(['infer', '-i', test_input, '-o', test_output, '-r', 'fashion-v4', '-t', '0.5'])
