# Linux x86-64 onedir Phase 1

本阶段只构建 `dist/OneLine/`、`dist/OneLine-linux-x86_64.tar.gz` 和 `.sha256`。不会从 Intel Mac 交叉生成 Linux 二进制，也不会制作 onefile、deb、rpm、AppImage 或正式 Release。

手动触发 `.github/workflows/linux-x86_64-onedir.yml`。GitHub 的 Ubuntu runner 仅作为 Docker 宿主；真正的 Python 编译、Release Gate、PyInstaller、`ldd` 和冻结程序 smoke 全在 manylinux_2_28 x86-64 容器内执行。只有全部成功才上传 tar.gz、SHA256 和依赖报告。`build-linux.sh` 在任何 Release Test 失败时立即停止。

本机若有 Docker，可在 Linux x86-64 宿主按工作流同样的 `docker build` / `docker run` 命令执行。`scripts/build-linux.sh` 拒绝 macOS、非 x86-64 和非 `/workspace` 容器路径。

解压后运行：

```bash
tar -xzf OneLine-linux-x86_64.tar.gz
./OneLine/OneLine
```

目标机不需要 Python、pip 或 virtualenv。可先运行 `scripts/kylin-system-check.sh`（只读），并按 `docs/KYLIN_ACCEPTANCE_CHECKLIST.md` 逐项验收。

## 构建边界

- 基线：manylinux_2_28 (AlmaLinux 8 / glibc 2.28)。不能仅凭该基线推断所有银河麒麟 V10 版本兼容，目标机必须实测 `glibc` 与 CPU 架构。
- Python 3.13.5 从官方源码构建共享 `libpython`；SHA256 固定在 Dockerfile。PyInstaller 不能依赖可能缺少共享库的 manylinux 轮子构建解释器。
- `requirements-runtime.txt` 固定门禁验证过的 PyQt5、Qt 与 sip 版本；`requirements-build.txt` 固定 PyInstaller、hooks、pytest 及其依赖。开发工具不进入正式包。
- `source-baseline.sha256` 冻结编辑核心和相关生产模块。需要变更时先另行评审、更新 Release Gate，再有意识地更新哈希。打包脚本不会改动这些文件。
- spec 显式收集 xcb、offscreen 插件；平台插件和关键 Qt 库必须通过 `ldd`。不要将 glibc、系统 loader 或全部 X11 库盲目复制进包。
- `QT_QPA_PLATFORM=offscreen` 的冻结程序 smoke 只证明无显示环境下可构造 Qt/窗口/编辑器/Overlay 并插入文本；不证明银河麒麟 GUI、中文 IME 或 X11/XWayland 兼容。

## 已验证候选

2026-10-14 的成功构建对应提交 `7552fe0c5f9b9396fbd0bb15d19343b96b1f5a9d`，候选分支为 `codex/linux-x86_64-rc1`；[Actions 运行 #38520061426](https://github.com/Lucas-Evan/OneLine/actions/runs/38520061426) 含可下载 tar.gz、SHA256 和依赖报告。`source-baseline.sha256` 额外校验稳定生产模块，不替代 Git 提交。该 artifact 尚未经过银河麒麟实机 GUI 验收。
