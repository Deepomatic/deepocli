#!/bin/bash

set -xe

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

export PYENV_VERSION="$1"

if [ -z "$PYENV_VERSION" ]; then
    echo "PYENV_VERSION required"
    exit 1;
fi

# Used by coveragepy
# avoid using the same file for parallel builds
export COVERAGE_FILE=".coverage.$PYENV_VERSION"

venv_dirname="venv-$PYENV_VERSION"
dist_dirname="dist-$PYENV_VERSION"
build_dirname="build-$PYENV_VERSION"

function cleanup {
    deactivate
    rm -rf $dist_dirname $build_dirname $venv_dirname $COVERAGE_FILE
}

rm -rf $dist_dirname $build_dirname $venv_dirname $COVERAGE_FILE

# create isolated virtualenv
virtualenv $venv_dirname

# cleanup on error
trap cleanup EXIT

source $venv_dirname/bin/activate
pip install -r ${CURRENT_DIR}/requirements.dev.txt

# linter
flake8 --statistics --verbose

mkdir -p $build_dirname
# install deepocli
python setup.py \
       egg_info --egg-base $build_dirname \
       build_py --build-lib $build_dirname \
       bdist_wheel --dist-dir $dist_dirname --bdist-dir $build_dirname

pip install $dist_dirname/deepomatic_cli-*.whl \
      --no-cache-dir --force-reinstall \
      --ignore-installed --upgrade


# unit tests
main_pyversion="${PYENV_VERSION%.*}"
pytest --junit-xml=junit-py/${main_pyversion}.xml --cov=deepomatic/ \
       --cov-report=xml:coverage-py/${main_pyversion}.xml \
       --cov-report html:cover-py/${main_pyversion} --color=yes \
       -vv


# Check that opencv can be found for all those platforms
opencv=$(grep opencv-python requirements.txt)
platforms="
macosx_10_9_intel
macosx_10_9_x86_64
macosx_10_10_intel
macosx_10_10_x86_64
macosx_10_11_x86_64
macosx_10_12_x86_64
macosx_10_13_x86_64
macosx_10_14_x86_64
macosx_10_15_x86_64
win32
win_amd64
"
for platform in $platforms; do
    pip download --platform $platform \
        --python-version=$main_pyversion \
        --no-deps "$opencv" -d /tmp
done
