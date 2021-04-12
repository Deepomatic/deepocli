#!/bin/bash

set -xe

# Useful to have a working home (notably for pip commands), otherwise HOME is `/`, which is not writable with DMAKE_UID!=0
export HOME=/tmp/home
mkdir -p $HOME

pip install -e .

cat <<"EOF" >> ~/.bashrc

# activate deepomatic-cli autocomplete
eval "$(register-python-argcomplete deepo)"
EOF

exec "$@"
