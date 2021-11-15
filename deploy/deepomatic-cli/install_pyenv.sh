#!/bin/bash

set -xe
export PATH="/opt/pyenv/shims:/opt/pyenv/bin:$PATH"
export PYENV_ROOT="/opt/pyenv"
export PYENV_SHELL="bash"
export CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Generate locales
locale-gen en_US.UTF-8
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# Install pyenv
git clone -b "v2.2.0" --single-branch --depth 1 https://github.com/pyenv/pyenv.git $PYENV_ROOT
python_versions=`cat deploy/deepomatic-cli/python-versions.txt`

# prepare all defined python versions for isolated testing
for version in $python_versions; do
    pyenv install $version;
    export PYENV_VERSION=$version
    pip install --upgrade pip==21.3.1
    pip install virtualenv==20.10.0
done
unset PYENV_VERSION

# prepare first defined python version for development
pyenv global $python_versions

# Allow pip install in entrypoint when DMAKE_UID != 0
chmod -R go=u $PYENV_ROOT

find $PYENV_ROOT/versions -type d '(' -name '__pycache__' -o -name 'test' -o -name 'tests' ')' -exec rm -rf '{}' +
find $PYENV_ROOT/versions -type f '(' -name '*.pyo' -o -name '*.exe' ')' -exec rm -f '{}' +
