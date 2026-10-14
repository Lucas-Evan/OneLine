#!/usr/bin/env bash
# Read-only environment inventory for a real Kylin V10 x86-64 machine.
set -u

echo '=== kernel / architecture ==='
uname -a
uname -m
echo
echo '=== OS ==='
if [[ -r /etc/os-release ]]; then
  sed -n '/^\(NAME\|VERSION\|ID\|VERSION_ID\|PRETTY_NAME\)=/p' /etc/os-release
else
  echo '/etc/os-release unavailable'
fi
echo
echo '=== glibc ==='
getconf GNU_LIBC_VERSION 2>/dev/null || ldd --version 2>/dev/null | head -n 1
echo
echo '=== display session ==='
printf 'XDG_SESSION_TYPE=%s\n' "${XDG_SESSION_TYPE:-unset}"
printf 'DISPLAY=%s\n' "${DISPLAY:-unset}"
if [[ -n "${WAYLAND_DISPLAY:-}" ]]; then
  echo 'WAYLAND_DISPLAY=present'
else
  echo 'WAYLAND_DISPLAY=absent'
fi
printf 'XDG_CURRENT_DESKTOP=%s\n' "${XDG_CURRENT_DESKTOP:-unset}"
printf 'DESKTOP_SESSION=%s\n' "${DESKTOP_SESSION:-unset}"
echo
echo '=== fonts (first 20 families) ==='
if command -v fc-list >/dev/null 2>&1; then
  fc-list : family 2>/dev/null | sort -u | head -n 20
else
  echo 'fontconfig/fc-list unavailable'
fi
echo
echo '=== X11 / xcb library availability ==='
if command -v ldconfig >/dev/null 2>&1; then
  ldconfig -p 2>/dev/null | grep -E 'lib(X11|X11-xcb|xcb|xkbcommon|GL|fontconfig|freetype)\.so' | sort || true
else
  echo 'ldconfig unavailable; check system library package database manually'
fi
echo
echo 'Read-only check complete; no system files were changed.'
