#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -x .venv/bin/python ]]; then
  echo "尚未创建开发环境，请先运行 ./scripts/bootstrap-macos.sh" >&2
  exit 1
fi

QT_QPA_PLATFORM=offscreen exec .venv/bin/python -m pytest -m release -q "$@"
