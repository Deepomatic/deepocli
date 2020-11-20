#!/bin/bash

set -xe
export DEBIAN_FRONTEND="noninteractive"
export PYENV_ROOT="/opt/pyenv"
export PATH="/opt/pyenv/shims:/opt/pyenv/bin:$PATH"
export PYENV_ROOT="/opt/pyenv"
export PYENV_SHELL="bash"
export CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

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
                          libgl1-mesa-glx \
                          tk-dev

# Generate locales
locale-gen en_US.UTF-8
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# Install pyenv
git clone -b "v1.2.21" --single-branch --depth 1 https://github.com/pyenv/pyenv.git $PYENV_ROOT
python_versions=`cat ${CURRENT_DIR}/python-versions.txt`
# prepare all defined python versions for isolated testing
for version in $python_versions; do
    pyenv install $version;
    export PYENV_VERSION=$version
    pip install --upgrade pip==20.2.4
    pip install virtualenv==20.1.0
done
unset PYENV_VERSION
# prepare first defined python version for development
pyenv global $python_versions
pip install -r ${CURRENT_DIR}/requirements.dev.txt
pip install -e .

find $PYENV_ROOT/versions -type d '(' -name '__pycache__' -o -name 'test' -o -name 'tests' ')' -exec rm -rf '{}' +
find $PYENV_ROOT/versions -type f '(' -name '*.pyo' -o -name '*.exe' ')' -exec rm -f '{}' +

rm -rf /var/lib/apt/lists/* /tmp/* || :
