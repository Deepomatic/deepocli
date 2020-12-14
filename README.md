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

# FAQ

## `opencv-python` (-headless) installation takes forever

Depending on your pip version, it might rebuild it from source. We require upgrading pip to >= 19.3.

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


# Bugs

Please send bug reports to support@deepomatic.com
