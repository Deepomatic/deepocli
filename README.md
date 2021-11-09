# deepomatic-command-line-interface

[Deepomatic](https://www.deepomatic.com) Command Line Interface.

This command line interface has been made to help you interact with our services via the command line.

[![Build Status](https://travis-ci.com/Deepomatic/deepocli.svg?branch=master)](https://travis-ci.com/Deepomatic/deepocli)

# CLI Documentation

Find the complete documentation at [docs.deepomatic.com/deepomatic-cli/](https://docs.deepomatic.com/deepomatic-cli/)

# Installation

```bash
pip install deepomatic-cli
```

If you need rpc support, prefer:
```bash
# requires deeomatic-rpc package to be installed
pip install deepomatic-cli[rpc]
```

## Autocompletion

To activate the autocompletion the easiest way is to add the following line to your shell config file:

```bash
eval "$(register-python-argcomplete deepo)"
```

For example if you use bash:

```bash
cat <<"EOF" >> ~/.bashrc

# activate deepomatic-cli autocomplete
eval "$(register-python-argcomplete deepo)"
EOF
```

(If it slows down your shell startup too much, you can pre-generate the completion into a static file then source it in your `.bashrc`: that doesn't change when deepo-cli is updated (except when updating `argcomplete` itself).)

For more information, checkout the documentation of [argcomplete](https://github.com/kislyuk/argcomplete)

# FAQ

## `opencv-python` (-headless) installation takes forever

Depending on your pip version, it might rebuild it from source. 19.3 is the minimum supported version
- Check version with `pip -V`
- Update with `pip install 'pip>=19.3'`

## Window output doesn't work. I get a `cv2.error`.

`deepomatic-cli` ships with `opencv-python-headless` as most of the features don't need a GUI.
This also avoids requiring libGL on the system (it is for example usually not there in docker containers).
If you want to use the GUI features, we recommend installing `opencv-python` after installing `deepomatic-cli`:
```bash
pip install deepomatic-cli
opencv_install=$(pip3 freeze | grep opencv-python-headless | sed 's/-headless//g')
pip uninstall opencv-python-headless
pip install $opencv_install
```

## About the output video codec

The CLI makes heavy use of OpenCV which does not provide the ability to configure the video encoder settings.
We can choose the codec to use (FourCC), but we can't choose the bitrate, quality, number of pass, profile or any other settings.
The quality chosen by OpenCV remains a small mystery, it seems to vary depending on the codec.

If for some reason the output video encoding does not suit you (too heavy, bad quality), here are our options:

### Changing the FourCC

Set the `--fourcc` option of the CLI. The `opencv-python` package only provide the codecs which have a free license.
This means you will not be able to choose `avc1` or `hevc`. We provide a dockerfile and an installation script to rebuild `opencv-python` with x264 encoder (corresponding to `acv1` FourCC).
The readme can be found [here](docker/README.md). Please makes sure you can use it (it is patented and not free).

If you are on windows, there is an alternative using [openh264](https://github.com/cisco/openh264):
- Download the [library](https://github.com/cisco/openh264/releases) (should work with openh264-1.7.0-win64.dll.bz2)
- Extract the archive in `C:\Windows\System32` or in the same directory where the CLI command is launched

### Piping to ffmpeg or cvlc

If you want more freedom on the encoding settings we suggest piping the CLI to `ffmpeg` or `cvlc` by using the option `-o stdout`.
In both case you need to tell `ffmpeg` or `cvlc` about the resolution, framerate and color space of the input stream.
You can use `ffprobe` or `mediainfo` to get the resolution and framerate of your input video.
The color space (chroma) does not depend on your input video but on our CLI which by default output BGR color space.

#### Example using `ffmpeg`

```bash
deepo platform model noop -i $input_video -o stdout | ffmpeg -f rawvideo -pixel_format bgr24 -video_size 1280x720 -framerate 15 -i - -c:v h264 $output_video
```

#### Example using `cvlc`

BGR color space is not supported by `cvlc`, you will need to ask our CLI to convert the stream to `RGB`.

```bash
deepo platform model noop -i $input_video -o stdout --output_color_space RGB | cvlc --demux=rawvideo --rawvid-fps=15 --rawvid-width=1280 --rawvid-height=720 --rawvid-chroma=RV24 - --sout "#transcode{vcodec=h264}:std{access=file,dst=$output_video}"
```


# Bugs

Please send bug reports to support@deepomatic.com
