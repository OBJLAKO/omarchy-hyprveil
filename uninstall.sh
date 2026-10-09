#!/usr/bin/env bash
set -euo pipefail
SRC="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SRC/tools/setup.py" ]]; then
    exec /usr/bin/python3 "$SRC/tools/setup.py" --uninstall "$@"
fi
exec /usr/bin/python3 "$SRC/setup.py" --uninstall "$@"
