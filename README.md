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


# Bugs

Please send bug reports to support@deepomatic.com
