#!/bin/bash
set -xe

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

concurrency="${1:-6}"

rm -rf venv-*
pyenv global  | parallel -j $concurrency --halt now,fail=1 --lb --tagstring '\033[0;34m[{}]\033[0m' ${CURRENT_DIR}/run_test.sh {}


# TODO: download for mac and windows
# put cover files in directories
