#!/usr/bin/env bash
set -euo pipefail
SRC="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec /usr/bin/python3 "$SRC/tools/setup.py" "$@"
