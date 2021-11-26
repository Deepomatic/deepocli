import os
import pytest
import subprocess
import tempfile
import hashlib
import uuid
from utils import init_files_setup, DEFAULT_RECOGNITION

INPUTS = init_files_setup()

DEEPOCLI_TO_FFMPEG_PIXEL_FORMAT = {
    'BGR': 'bgr24',
    'RGB': 'rgb24',
    'YUV420': 'yuv420p',
    'GRAY': 'gray',
}

@pytest.mark.parametrize(
    'infer_cmd,color_space,expected_hash', [
        ('infer', 'BGR', 'cafba1802a615d7c00122444937c7ea81e084db0cabc5bce18143dffe3534822'),
        ('draw', 'BGR', '0a8da0d3989d2a8c00082054bbf449556dff10f6432086740604244fb34799a0'),
        ('blur', 'BGR', '87e3690904d75a783f9bd796a0a1a457f259580f275150bff25ce7404421aa69'),
        ('noop', 'BGR', 'cafba1802a615d7c00122444937c7ea81e084db0cabc5bce18143dffe3534822'),

        ('infer', 'RGB', 'bd852a31b145265a412fa90a19b367c3b5ad730fa41e85b13959792641f30207'),
        ('draw', 'RGB', '926ee1e5af5e44c2cf08c874d0556c4f1abfe7b3b63f831283b8313a985a31c1'),
        ('blur', 'RGB', '9ea0d6db7fd29e79994ebb0998eca476036185a29f7c877b52a4c0df8f54f5ce'),
        ('noop', 'RGB', 'bd852a31b145265a412fa90a19b367c3b5ad730fa41e85b13959792641f30207'),

        ('infer', 'GRAY', '869d300900a902cb5fa622528c551cf3a9305fddc2a64073da8f99d49a8f8cf0'),
        ('draw', 'GRAY', 'b3a9302692fcb40921bd362e6c0592d6dda9f206f8ec1a968cb529e278e9e75f'),
        ('blur', 'GRAY', 'ac6f2057602e1e92bd59c0084740904d858508f49205584731f71d8b85f77ddc'),
        ('noop', 'GRAY', '869d300900a902cb5fa622528c551cf3a9305fddc2a64073da8f99d49a8f8cf0'),

        ('infer', 'YUV420', 'cc41aa34e0b4c7e24c8e261c301a5fb1130b7e4944698eda4d05c22df3900c3f'),
        ('draw', 'YUV420', 'dbd17585bc48be8e44bfa370635725837913353956d58d7ad3ba746b5843b836'),
        ('blur', 'YUV420', 'e63448ebec9e78743c2cd1aa728d445db278a7ced8ff38ff057cc9870031fabd'),
        ('noop', 'YUV420', 'cc41aa34e0b4c7e24c8e261c301a5fb1130b7e4944698eda4d05c22df3900c3f'),
    ])
def test_piping_ffmpeg(infer_cmd, color_space, expected_hash):
    if infer_cmd != 'noop':
        cli_args = '-r ' + DEFAULT_RECOGNITION
    else:
        cli_args = ''
    cmd_base = 'deepo platform model {} -i {} {} -o stdout --output_color_space {} | ffmpeg -f rawvideo -pixel_format {} -video_size 640x360 -framerate 23.98 -i - -c:v {} {}'
    codec = 'mpeg4'

    ffmpeg_pixel_format = DEEPOCLI_TO_FFMPEG_PIXEL_FORMAT[color_space]

    video_filename = INPUTS['VIDEO']
    _, suffix = os.path.splitext(video_filename)

    basename = str(uuid.uuid4()) + suffix
    output_video = os.path.join(tempfile.gettempdir(), basename)
    try:
        cmd = cmd_base.format(infer_cmd, video_filename, cli_args, color_space, ffmpeg_pixel_format, codec, output_video)
        subprocess.run(cmd, shell=1, check=1)
        # Maybe compare ssim / psnr instead of hash if default params of ffmpeg changes
        with open(output_video, 'rb') as f:
            assert hashlib.sha256(f.read()).hexdigest() == expected_hash
    finally:
        if os.path.exists(output_video):
           os.remove(output_video)
