#!/bin/bash

set -xe

pip install -e .

eval "$(register-python-argcomplete deepo)"

exec "$@"
