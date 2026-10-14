# OneLine Linux Packaging Phase 1 Report

状态：**A — onedir artifact 已准备好，可以转银河麒麟实机验证。** 日期：2026-10-14。

## 1. 发布候选与修改文件

成功构建提交：`7552fe0c5f9b9396fbd0bb15d19343b96b1f5a9d`；保留候选分支 `codex/linux-x86_64-rc1`。开始时本地仓库尚无首个提交、无 remote；用户提供的 GitHub 仓库已有 `a4a0917`，其生产文件与本地同名文件一致。用户明确允许将本阶段源码、测试与打包配置推送到公开仓库。远端原有历史和 `LICENSE` 均保留。

本阶段新增 `.github/workflows/linux-x86_64-onedir.yml`、`.dockerignore`、`packaging/OneLine.spec`、`packaging/linux/` 内的 Dockerfile、锁定依赖、入口、基线哈希及说明、`packaging/LICENSE_NOTES.md`、`scripts/build-linux.sh`、`scripts/smoke-linux-build.sh`、`scripts/kylin-system-check.sh`、`docs/KYLIN_ACCEPTANCE_CHECKLIST.md`。同步纳入现有测试和文档，调整 `.gitignore`；为 Linux offscreen 字体渲染与非 root 权限测试做了测试/CI 层适配。CI 中发现的问题只修正 spec 路径和构建容器 XCB 依赖。**未修改** `editor.py`、`visual_line_overlay.py`、`window.py` 或 QTextDocument、输入、删除、光标、滚动、IME 流程。`packaging/linux/source-baseline.sha256` 在 CI 中核验了 8 个稳定生产模块。

## 2–6. 构建环境、依赖和 spec

- 工作流：[运行 #38520061426](https://github.com/Lucas-Evan/OneLine/actions/runs/38520061426)，手动 `workflow_dispatch`，结论 `success`。Ubuntu runner 仅作 Docker 宿主；实际构建使用 `quay.io/pypa/manylinux_2_28_x86_64:2026.05.07-2`，报告显示 AlmaLinux 8.10、x86_64、glibc 2.28。该次容器 image ID：`sha256:35ff8407e9f6a578125a66801616f13283b686f481a15998fdd8d109b66e3223`。
- Python 3.13.5：固定源码 SHA256，从官方源码构建共享 libpython；编译目标 `-march=x86-64 -mtune=generic`。PyQt5 5.15.11、Qt runtime 5.15.19、PyQt5-sip 12.20.0。PyInstaller 6.15.0、hooks-contrib 2025.8；构建测试依赖不作为应用目录内容。
- `packaging/OneLine.spec` 只做 onedir，入口为 `packaging/linux/frozen_entry.py`，显式纳入 `libqxcb.so`、`libqoffscreen.so`，排除 pytest、测试目录与常见开发模块；无图标或其他发行资源。CPython、PyQt 与 PyInstaller 版本均锁定，未升级已验证的 PyQt5。
- Dockerfile 仅为构建/`ldd` 检查安装 XCB 与 xkbcommon 系统依赖；不盲目将 glibc、loader 或全部 X11 库复制进发行物。目标机依赖仍须现场检查。

## 7–9. Linux Release Gate、smoke 与动态依赖

CI 顺序：生产源码哈希校验 → `pip check` → Linux offscreen Release Gate → PyInstaller → ELF / Qt 插件 / `ldd` 检查 → **冻结后的** OneLine offscreen smoke → tar.gz / SHA256 → 上传。

- Linux Release Gate：**69 passed，2 skipped，49 deselected**；测试失败会阻止打包。既有 macOS Cocoa Gate 为 71 passed，本轮未重复，不声称麒麟 GUI 已通过。
- PyInstaller onedir：成功。冻结程序输出 `ONELINE_SMOKE_OK`，随后脚本输出 `ONELINE_LINUX_SMOKE_OK`；已创建 QApplication、窗口、Editor、Overlay，插入合成测试文本并正常退出。
- `file` 确认主程序为 Linux x86-64 ELF。构建报告对主程序、`libqxcb.so`、`libqoffscreen.so` 和 `libQt5Core.so.5` 执行 `ldd`；CI 检查未发现 `not found`。详细结果见 Actions artifact 中的 `packaging/linux/dependency-report.txt`。这只证明该构建容器中的依赖可解析。
- Mac 开发机未构建 Linux 二进制；`build-linux.sh` 会拒绝 macOS 环境。

## 10–11. Artifact 与 SHA256

- 下载：[OneLine-linux-x86_64-onedir（Actions artifact）](https://github.com/Lucas-Evan/OneLine/actions/runs/38520061426/artifacts/11873098074)。Artifact ID `11873098074`，ZIP 大小 **64,280,301 bytes**，包含 tar.gz、校验文件和依赖报告；当前 GitHub 元数据标示未过期。
- `dist/OneLine-linux-x86_64.tar.gz`：**64,850,061 bytes**；SHA256：`d865620fdb744a5a5aca804d0f0b2055527a6071d796e702a779b34d8bc37b4b`。CI 的 `sha256sum --check` 通过；下载 ZIP 后再次独立计算 tar.gz 哈希，与校验文件一致。
- Artifact ZIP SHA256：`faba163343d2ba5ac4055afd44b260caab1ebd5409cc9f2bfbf571d23aada6da`，与 GitHub artifact 元数据一致。ZIP 完整性检查通过。
- 解压 tar.gz 后的入口：`./OneLine/OneLine`；不需要目标机 Python、pip 或 virtualenv。

## 12–13. 已知风险与银河麒麟实机步骤

本次 `offscreen` smoke **不等于** 银河麒麟 V10 的真实桌面验收。目标机的 glibc 版本、兆芯 x86-64 指令兼容、X11/XWayland、`libqxcb.so` 所需系统库、Qt 字体/中文 IME、托盘、窗口管理器与全局快捷键均待现场确认。容器镜像固定 tag 而未固定 digest，后续可提高供应链复现性。正式分发前须处理 `packaging/LICENSE_NOTES.md` 中的 PyQt5 许可事项；本报告不作法律结论。

在目标机先运行只读 `scripts/kylin-system-check.sh`，核对架构、glibc 和显示会话；再校验 tar.gz SHA256、解压、执行 `./OneLine/OneLine`，按 `docs/KYLIN_ACCEPTANCE_CHECKLIST.md` 逐项检查。遇到 xcb 启动错误，先使用 `QT_DEBUG_PLUGINS=1` 和 `ldd` 定位真正缺失项，不修改系统 Qt、glibc、loader 或 `LD_LIBRARY_PATH`。

本阶段结论仅为 **A — artifact 可供麒麟实机验证**；不代表麒麟兼容性已通过。未开始 onefile、deb、rpm、AppImage、安装器、自动更新或正式 GitHub Release。
