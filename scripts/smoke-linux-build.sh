#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
  echo "smoke 仅可在 Linux x86_64 执行。" >&2
  exit 1
fi

bundle=dist/OneLine
binary="$bundle/OneLine"
internal="$bundle/_internal"
xcb="$internal/PyQt5/Qt5/plugins/platforms/libqxcb.so"
offscreen="$internal/PyQt5/Qt5/plugins/platforms/libqoffscreen.so"
report=packaging/linux/dependency-report.txt

for target in "$binary" "$xcb" "$offscreen"; do
  if [[ ! -f "$target" ]]; then
    echo "发行物缺少必需文件: $target" >&2
    exit 1
  fi
done
if [[ ! -x "$binary" ]]; then
  echo "主程序没有可执行权限。" >&2
  exit 1
fi
if ! file "$binary" | grep -q 'ELF 64-bit.*x86-64'; then
  echo "主程序不是 Linux x86-64 ELF。" >&2
  exit 1
fi

qtcore=$(find "$internal" \( -type f -o -type l \) -name 'libQt5Core.so.5' -print -quit)
if [[ -z "$qtcore" ]]; then
  echo "发行物缺少 libQt5Core.so.5。" >&2
  exit 1
fi

{
  echo 'OneLine Linux x86-64 dependency report'
  echo 'Build userspace: manylinux_2_28_x86_64 (AlmaLinux 8 baseline)'
  echo "Architecture: $(uname -m)"
  echo "OS ID: $(. /etc/os-release; echo "$ID")"
  echo "OS VERSION_ID: $(. /etc/os-release; echo "$VERSION_ID")"
  echo "glibc: $(getconf GNU_LIBC_VERSION)"
  python3.13 -c 'import sys; print("Python: " + sys.version.split()[0])'
  python3.13 -c 'from PyQt5.QtCore import PYQT_VERSION_STR, qVersion; print("PyQt5: " + PYQT_VERSION_STR); print("Qt runtime: " + qVersion())'
  python3.13 -c 'import PyInstaller; print("PyInstaller: " + PyInstaller.__version__)'
  echo
  echo 'file OneLine:'
  file "$binary"
  for target in "$binary" "$xcb" "$offscreen" "$qtcore"; do
    echo
    echo "ldd ${target#dist/OneLine/}:"
    ldd "$target" | sed 's#/workspace/#./#g'
  done
} > "$report"

if grep -q 'not found' "$report"; then
  echo "ldd 发现缺失的动态库，请检查 $report。" >&2
  grep 'not found' "$report" >&2
  exit 1
fi

# Exercise the actual frozen executable without a display or user data.
QT_QPA_PLATFORM=offscreen timeout 30 "$binary" --packaging-smoke

# No development/test content is allowed in the onedir tree.
if find "$bundle" -type d \( -name tests -o -name __pycache__ -o -name .pytest_cache \) \
    -print -quit | grep -q .; then
  echo "发行物包含开发缓存或测试目录。" >&2
  exit 1
fi
echo "ONELINE_LINUX_SMOKE_OK"
