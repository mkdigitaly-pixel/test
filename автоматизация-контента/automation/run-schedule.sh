#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
# One launcher; publish.py also locks direct schedule invocations.
exec 9>../queue/.launcher.lock
flock -n 9 || exit 0
python3 publish.py schedule run
python3 save-publication-state.py
