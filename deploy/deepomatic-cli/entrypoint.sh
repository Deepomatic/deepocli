#!/bin/bash

set -xe

pip install -e .

cat <<"EOF" >> ~/.bashrc

# activate deepomatic-cli autocomplete
eval "$(register-python-argcomplete deepo)"
EOF

exec "$@"
