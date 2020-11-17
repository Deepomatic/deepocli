#!/bin/bash

set -xe
export DEBIAN_FRONTEND="noninteractive"
export PYENV_ROOT="/opt/pyenv"
export PATH="/opt/pyenv/shims:/opt/pyenv/bin:$PATH"
export PYENV_ROOT="/opt/pyenv"
export PYENV_SHELL="bash"
export CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

apt-get update && apt-get install -y --no-install-recommends \
                          build-essential \
                          ca-certificates \
                          curl \
                          git \
                          libbz2-dev \
                          libffi-dev \
                          libncurses5-dev \
                          libncursesw5-dev \
                          libreadline-dev \
                          libsqlite3-dev \
                          libssl1.0-dev \
                          liblzma-dev \
                          llvm \
                          make \
                          netbase \
                          pkg-config \
                          tk-dev \
                          wget \
                          xz-utils \
                          zlib1g-dev \
                          libgl1-mesa-glx

# Install pyenv
git clone -b "v1.2.21" --single-branch --depth 1 https://github.com/pyenv/pyenv.git $PYENV_ROOT
python_versions=`cat ${CURRENT_DIR}/python-versions.txt`
for version in $python_versions; do
    pyenv install $version;
    export PYENV_VERSION=$version
    pip install --upgrade pip==20.2.4
    pip install -r ${CURRENT_DIR}/requirements.dev.txt
done
unset PYENV_VERSION
pyenv global $python_versions
pip install -e .

find $PYENV_ROOT/versions -type d '(' -name '__pycache__' -o -name 'test' -o -name 'tests' ')' -exec rm -rf '{}' +
find $PYENV_ROOT/versions -type f '(' -name '*.pyo' -o -name '*.exe' ')' -exec rm -f '{}' +

# Install parallel
cd /tmp
wget https://ftp.gnu.org/gnu/parallel/parallel-20201022.tar.bz2 -O parallel.tar.bz2
tar xvf parallel.tar.bz2
cd parallel-*
./configure --prefix=/usr
make install
# Ignore exit code (seem to return != 0 even when valid)
echo 'will cite' | parallel --citation || true

rm -rf /var/lib/apt/lists/* /tmp/* || :
