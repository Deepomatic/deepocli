#!/bin/bash

export DEBIAN_FRONTEND="noninteractive"

# install the minimum dependencies to build and use python
# some modules might not work like `curses` but we don't need them
apt-get update && apt-get install -y --no-install-recommends \
                          build-essential \
                          ca-certificates \
                          locales \
                          curl \
                          git \
                          wget \
                          parallel \
                          libbz2-dev \
                          libffi-dev \
                          libreadline-dev \
                          libsqlite3-dev \
                          libssl-dev \
                          liblzma-dev \
                          zlib1g-dev \
                          ffmpeg \
                          tk-dev

rm -rf /var/lib/apt/lists/* /tmp/* || :
