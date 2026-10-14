#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
  echo "仅允许在 Linux x86_64 构建；macOS 不可交叉生成本发行物。" >&2
  exit 1
fi
if [[ "$(pwd)" != /workspace ]]; then
  echo "必须在受控构建容器的 /workspace 挂载目录运行。" >&2
  exit 1
fi

sha256sum --check packaging/linux/source-baseline.sha256
python3.13 -c 'import sys; assert sys.version_info[:3] == (3, 13, 5), sys.version'
python3.13 -m pip check

# A failing release test aborts the script before PyInstaller is invoked.
QT_QPA_PLATFORM=offscreen python3.13 -m pytest -m release -q

python3.13 -m PyInstaller --clean --noconfirm \
  --distpath dist --workpath build/pyinstaller \
  packaging/OneLine.spec

bash scripts/smoke-linux-build.sh

tar -czf dist/OneLine-linux-x86_64.tar.gz -C dist OneLine
sha256sum dist/OneLine-linux-x86_64.tar.gz > dist/OneLine-linux-x86_64.sha256
sha256sum --check dist/OneLine-linux-x86_64.sha256

echo "Linux onedir artifact: dist/OneLine-linux-x86_64.tar.gz"
echo "SHA256 file: dist/OneLine-linux-x86_64.sha256"
