#!/bin/bash

set -xe

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

export PYENV_VERSION="$1"

if [ -z "$PYENV_VERSION" ]; then
    echo "PYENV_VERSION required"
    exit 1;
fi

venv_dirname="venv-$PYENV_VERSION"
dist_dirname="dist-$PYENV_VERSION"
build_dirname="build-$PYENV_VERSION"

function cleanup {
    deactivate
    rm -rf $dist_dirname $build_dirname $venv_dirname
}

rm -rf $dist_dirname $build_dirname $venv_dirname
# create isolated virtualenv
virtualenv $venv_dirname
source $venv_dirname/bin/activate
pip install -r ${CURRENT_DIR}/requirements.dev.txt
# linter
flake8 --statistics --verbose deepomatic tests
# install deepocli
python setup.py bdist_wheel \
       --dist-dir $dist_dirname \
       --bdist-dir $build_dirname

pip install $dist_dirname/deepomatic_cli-*.whl \
    --build $build_dirname \
    --no-cache-dir --force-reinstall \
    --ignore-installed --upgrade
# unit tests
main_pyversion="${PYENV_VERSION%.*}"
python -m pytest --junit-xml=junit-py${main_pyversion}.xml --cov=deepomatic/ \
       --cov-report=xml:coverage-py${main_pyversion}.xml \
       --cov-report html:cover-py${main_pyversion} --color=yes -vv tests

trap cleanup EXIT
