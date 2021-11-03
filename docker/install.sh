#!/bin/bash

set -xe

git clone --recursive --single-branch -b ${OPENCV_PYTHON_TAG}  https://github.com/opencv/opencv-python.git

cd opencv-python

export CMAKE_ARGS="-DWITH_FFMPEG=ON"
export ENABLE_CONTRIB=1
export ENABLE_HEADLESS=1
export MAKEFLAGS="-j$(nproc)"

pip3 wheel . --verbose
pip3 install opencv_contrib_python_headless-*.whl
