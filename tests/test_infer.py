import os
from download_files import init_files_setup, check_directory, create_tmp_dir
from deepomatic.cli.cli_parser import run


# ------- Files setup ------------------------------------------------------------------------------------------------ #

# Input to test: Image, Video, Directory, Json
image_input, video_input, directory_input, json_input, dir_output = init_files_setup()
# Output to test: Image, Video, Stdout, Json, Directory
std_output = 'stdout'
image_output = 'image_output%04d.jpg'
video_output = 'video_output.mp4'
json_output = 'test_output%04d.json'
outputs = [std_output, image_output, video_output, json_output]


# ------- Image Input Tests ------------------------------------------------------------------------------------------ #

def infer(input, outputs, *args, **kwargs):
    extra_opts = kwargs.pop('extra_opts', [])
    outputs_absolute = []
    with create_tmp_dir() as tmpdir:
        for output in outputs:
            if output == std_output:
                outputs_absolute.append(output)
            else:
                outputs_absolute.append(os.path.join(tmpdir, output))
        run(['infer', '-i', input, '-o'] + outputs_absolute + ['-r', 'fashion-v4'] + extra_opts)
        check_directory(tmpdir, *args, **kwargs)


def test_e2e_image_infer_image():
    infer(image_input, [image_output], expect_nb_image=1)


def test_e2e_image_infer_video():
    infer(image_input, [video_output], expect_nb_video=1)


def test_e2e_image_infer_stdout():
    infer(image_input, [std_output])


def test_e2e_image_infer_json():
    infer(image_input, [json_output], expect_nb_json=1)


def test_e2e_image_infer_multiples():
    infer(image_input, outputs, 1, 1, 1)


# ------- Video Input Tests ------------------------------------------------------------------------------------------ #


def test_e2e_video_infer_image():
    infer(video_input, [image_output], expect_nb_image=21)


def test_e2e_video_infer_video():
    infer(video_input, [video_output], expect_nb_video=1)


def test_e2e_video_infer_stdout():
    infer(video_input, [std_output])


def test_e2e_video_infer_json():
    infer(video_input, [json_output], expect_nb_json=21)


def test_e2e_video_infer_multiples():
    infer(video_input, outputs, 21, 21, 1)


# ------- Directory Input Tests -------------------------------------------------------------------------------------- #


def test_e2e_directory_infer_image():
    infer(directory_input, [image_output], expect_nb_image=2)


def test_e2e_directory_infer_video():
    infer(directory_input, [video_output], expect_nb_video=1)


def test_e2e_directory_infer_stdout():
    infer(directory_input, [std_output])


def test_e2e_directory_infer_json():
    infer(directory_input, [json_output], expect_nb_json=2)


def test_e2e_directory_infer_multiples():
    infer(directory_input, outputs, 2, 2, 1)


# ------- Json Input Tests ------------------------------------------------------------------------------------------- #


def test_e2e_json_infer_image():
    infer(json_input, [image_output], expect_nb_image=1)


def test_e2e_json_infer_video():
    infer(json_input, [video_output], expect_nb_video=1)


def test_e2e_json_infer_stdout():
    infer(json_input, [std_output])


def test_e2e_json_infer_json():
    infer(json_input, [json_output], expect_nb_json=1)


def test_e2e_json_infer_multiples():
    infer(json_input, outputs, 1, 1, 1)


# ------- Special Options Tests -------------------------------------------------------------------------------------- #


def test_e2e_image_infer_json_threshold():
    infer(image_input, [json_output], expect_nb_json=1, extra_opts=['-t', '0.5'])


def test_e2e_image_infer_json_studio():
    infer(image_input, [json_output], expect_nb_json=1, studio_format=True, extra_opts=['-s'])
