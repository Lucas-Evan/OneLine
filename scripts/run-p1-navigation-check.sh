#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -x .venv/bin/python ]]; then
  echo "缺少 .venv，请先运行 ./scripts/bootstrap-macos.sh" >&2
  exit 1
fi

export QT_QPA_PLATFORM=cocoa
exec .venv/bin/python scripts/p1_navigation_check.py "$@"
