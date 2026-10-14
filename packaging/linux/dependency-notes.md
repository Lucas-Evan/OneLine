# Linux 依赖与 ABI 说明

当前开发机门禁环境：Python 3.13.5、PyQt5 5.15.11、PyQt5-Qt5 5.15.19、PyQt5-sip 12.20.0。Linux 构建锁定这些版本；PyInstaller 6.15.0 和 `pyinstaller-hooks-contrib` 2025.8 仅属于构建环境。

目标构建容器：`quay.io/pypa/manylinux_2_28_x86_64:2026.05.07-2`，glibc 2.28，x86-64。构建时将容器 image ID、`getconf GNU_LIBC_VERSION` 和 `ldd` 结果记录到 Actions 日志/`dependency-report.txt`。镜像 tag 尚未固定 digest，是后续提高供应链复现性的事项；目标机仍需实测。构建不使用 `-march=native`，自编译 CPython 使用通用 `-march=x86-64 -mtune=generic`。

Qt 的 X11 启动依赖 `platforms/libqxcb.so` 及其动态依赖。spec 将 xcb 和 CI smoke 所需的 offscreen 平台插件纳入 onedir。构建容器安装对应的 XCB / xkbcommon 系统包，以便验证插件依赖；这不表示将所有系统库捆绑进 onedir。构建报告对主程序、两个平台插件和 `libQt5Core.so.5` 执行 `ldd`；任何 `not found` 都使构建失败。`ldd` 在构建容器通过，只表示该容器依赖完整，不代表麒麟机依赖完整。

在目标机若出现 `Could not load the Qt platform plugin "xcb"`：

```bash
QT_DEBUG_PLUGINS=1 ./OneLine/OneLine
ldd ./OneLine/_internal/PyQt5/Qt5/plugins/platforms/libqxcb.so
```

先读插件搜索路径和 `not found` 项，再判断是系统包缺失还是打包遗漏。不得用 `sudo` 乱复制 `.so`、替换系统 Qt/glibc/loader，或覆盖系统 `LD_LIBRARY_PATH`。本阶段只承诺 X11/XWayland 为验收目标；Wayland 原生运行不作为通过条件。
