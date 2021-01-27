#!/bin/bash

set -xe

pip install -e .

cat <<"EOF" > ~/.bashrc
eval "$(register-python-argcomplete deepo)"
EOF

exec "$@"
