FROM ubuntu:20.04

# Correspond to version 3.4.16.57 https://github.com/opencv/opencv-python/releases
ARG OPENCV_PYTHON_TAG=57

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3-dev python3-pip build-essential wget tar git \
    libglib2.0-0 libavutil-dev libswscale-dev libavresample-dev \
    libjpeg-dev libavcodec-dev libavformat-dev libpng-dev libtiff-dev libdc1394-22-dev libtbb2 libgtk2.0-dev

RUN pip3 install --upgrade pip

ADD ./install.sh .

RUN ./install.sh
