import os
import time
import pytest
import numpy
import subprocess
import tempfile
import hashlib
import uuid
import cv2
import logging
from skimage.metrics import structural_similarity
from utils import init_files_setup, DEFAULT_RECOGNITION


INPUTS = init_files_setup()

DEEPOCLI_TO_FFMPEG_PIXEL_FORMAT = {
    'BGR': 'bgr24',
    'RGB': 'rgb24',
    'YUV420': 'yuv420p',
    'GRAY': 'gray',
}


def video_ssim(filename_1, filename_2):
    reader_1 = cv2.VideoCapture(filename_1)
    assert reader_1.isOpened()
    reader_2 = cv2.VideoCapture(filename_2)
    assert reader_2.isOpened()
    ssim = 0
    nb_frame = 0
    while True:
        read_1, image_1 = reader_1.read()
        read_2, image_2 = reader_2.read()
        assert read_1 == read_2
        if not read_1:
            break
        nb_frame += 1
        ssim += structural_similarity(image_1, image_2, multichannel=True)
    res = float(ssim) / float(nb_frame)
    reader_1.release()
    reader_2.release()
    return res


def check_ssim(filename_1, filename_2, min_value):
    assert video_ssim(filename_1, filename_2) >= min_value


def check_color_diff(color_channel_1, color_channel_2, max_diff):
    diff = color_channel_1.astype(float) - color_channel_2.astype(float)
    assert (numpy.absolute(diff) <= max_diff).all()


def check_ssim_gray(filename_1, filename_2, min_value):
    check_ssim(filename_1, filename_2, min_value)
    reader_2 = cv2.VideoCapture(filename_2)
    assert reader_2.isOpened()
    while True:
        read_2, image_2 = reader_2.read()
        if not read_2:
            break

        b, g, r = cv2.split(image_2)
        # Because of encoding, all channels might not be totally equal
        check_color_diff(b, g, 4)
        check_color_diff(b, r, 4)

    reader_2.release()


@pytest.mark.parametrize(
    'infer_cmd,color_space,check_fn,check_args', [
        ('infer', 'BGR', check_ssim, [0.85]),
        ('draw', 'BGR', check_ssim, [0.6]),
        ('blur', 'BGR', check_ssim, [0.59]),
        ('noop', 'BGR', check_ssim, [0.85]),

        ('infer', 'RGB', check_ssim, [0.85]),
        ('draw', 'RGB', check_ssim, [0.6]),
        ('blur', 'RGB', check_ssim, [0.59]),
        ('noop', 'RGB', check_ssim, [0.85]),

        ('infer', 'GRAY', check_ssim_gray, [0.81]),
        ('draw', 'GRAY', check_ssim_gray, [0.6]),
        ('blur', 'GRAY', check_ssim_gray, [0.55]),
        ('noop', 'GRAY', check_ssim_gray, [0.81]),

        ('infer', 'YUV420', check_ssim, [0.85]),
        ('draw', 'YUV420', check_ssim, [0.6]),
        ('blur', 'YUV420', check_ssim, [0.59]),
        ('noop', 'YUV420', check_ssim, [0.85]),
    ])
def test_piping_ffmpeg(infer_cmd, color_space, check_fn, check_args):
    if infer_cmd != 'noop':
        cli_args = '-r ' + DEFAULT_RECOGNITION
    else:
        cli_args = ''
    cmd_base = ('deepo platform model {} -i {} {} -o stdout --output_color_space {} | '
                'ffmpeg -f rawvideo -pixel_format {} -video_size 640x360 -framerate 23.98 -i - -c:v {} {}')
    codec = 'mpeg4'

    ffmpeg_pixel_format = DEEPOCLI_TO_FFMPEG_PIXEL_FORMAT[color_space]

    video_filename = INPUTS['VIDEO']
    _, suffix = os.path.splitext(video_filename)

    basename = str(uuid.uuid4()) + suffix
    output_video = os.path.join(tempfile.gettempdir(), basename)
    try:
        cmd = cmd_base.format(infer_cmd, video_filename, cli_args, color_space, ffmpeg_pixel_format, codec, output_video)
        subprocess.run(cmd, shell=1, check=1)
        check_fn(video_filename, output_video, *check_args)
    finally:
        if os.path.exists(output_video):
           os.remove(output_video)
