#!/bin/bash

export PATH="/opt/pyenv/shims:/opt/pyenv/bin:$PATH"
export PYENV_ROOT="/opt/pyenv"
export PYENV_SHELL="bash"

pip install -r deploy/deepomatic-cli/requirements.dev.txt
pip install -r requirements.txt
