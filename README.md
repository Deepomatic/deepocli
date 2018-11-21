# Deepomatic Controller

This controller has been made in order to help you interact with our services via the command line.

[![Build Status](https://travis-ci.com/Deepomatic/deepocli.svg?branch=master)](https://travis-ci.com/Deepomatic/deepocli)

## Installation

Requirements: Python 2.7+ or 3.4+

```sh
pip install git+https://github.com/deepomatic/deepocli@v0.2.0 --process-dependency-links
```

## Setup

In order to use models which are deployed in our cloud, you will need to set your application ID and API key in `DEEPOMATIC_APP_ID` and `DEEPOMATIC_API_KEY` environment variables, respectively.

```sh
export DEEPOMATIC_APP_ID=xxxxxxxxxxxx
export DEEPOMATIC_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Inputs

The input of the command should be specified after the `-i` flag.

Valid inputs are:

- number: open the specified device (ex: 0 for the default webcam) as a video stream
- /path/to/file: open the specified file (image or video) if supported.

    supported format: `.bmp`, `.jpeg`, `.jpg`, `.jpe`, `.png`, `.avi`, `.mp4`
- /path/to/directory: open the supported images and videos in the directory
- network stream: open the specified network stream 

    supported network streams: `rtsp`, `http`

## Outputs

The output of the command should be specified after the `-o` flag.

Valid outputs are:

- /path/to/file: write the output to the specifed file.

    - For images or json, the name can contain a wildcard (e.g. `/tmp/frame%05d.json`) that will be replaced with the index in the sequence.
    - For videos, the output frames will be concatenated in a single file
- network stream: not implemented yet
- stdout: write the frame in the process' standard output, which can be piped to another process, e.g. vlc
    
    ```sh
    deepocli draw -i 0 -o stdout | vlc --demux=rawvideo --rawvid-fps=25 --rawvid-width=640 --rawvid-height=480 --rawvid-chroma=RV24 - --sout "#display"
    ```

If the -o flag is omitted, the output is shown in a window (full screen if the `--fullscreen` flag is present).
The output fps can be set using the `--output_fps` followed by a valid number.


## Commands

### `infer`: Performing inference only

"Inference" is the action of running your algorithm. Inference can be computed using the `Deepomatic` API, or locally using the `Deepomatic` SDK.

To use the deepomatic API, you need to provide the version ID of the recognition that you have trained:

```sh
deepocli infer -i your/path/to/a/file/or/directory -o /tmp/output%05d.json --recognition_id 123
```

To use the deepomatic SDK, if you are an on-premises customer, you also need to provide the network address of the message queue as well as the routing key used for the exchange.

```sh
deepocli infer -i your/path/to/a/file/or/directory -o /output%05d.json --recognition_id 123 --routing_key key --amqp_url amqp://address
```

### `draw`: Drawing bounding boxes

You can also call the `draw` command to additionally generate images and videos with tags and bounding boxes overlayed.

```sh
deepocli draw -i your/path/to/a/file/or/directory -o /tmp/output%05d.json --recognition_id 123
```
The `--draw_score` flag adds each bounding box score to the overlay


### `blur`: Blurring bounding boxes

You can also call the `blur` command to anonymize the input by blurring the detected boxes.

```sh
deepocli blur -i your/path/to/a/file/or/directory -o /tmp/output%05d.json --recognition_id 123
```
The `--blur_method` flag lets you specify the blur method

    pixel, gaussian, black


### `feedback`: Deepomatic Studio support

You can send images to Deepomatic Studio using the `feedback` command.
The input can be specified using the `path` flag, which can be either one or more files and one or more directories. The dataset and organisation should also be specified using the `--dataset_name` and `--org_slug` flags.

```sh
deepocli feedback --path your/path/to/a/file/or/directory --org_slug your_org_slug --dataset_name your_dataset_name
```
With the `--recursive` flag, the command will look for the files in all subdirectories.


## Bugs

Please send bug reports to support@deepomatic.com
