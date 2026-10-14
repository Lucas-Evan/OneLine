# OneLine Linux Packaging Phase 1 Report

状态：**B — Linux 构建仍有明确外部验证缺口，尚无可交付 tar.gz。** 日期：2026-10-14。

## 发布候选与变更范围

开始前检查：本地仓库无首个 Git commit、无 GitHub remote；整棵源码处于未跟踪状态。随后确认用户提供的远端 `main` 已有提交 `a4a0917`，其 12 个生产文件与本地同名文件一致。已从远端提交创建隔离的候选克隆，加入本阶段文件并生成候选提交；未覆盖远端历史，也未修改 `editor.py`、`visual_line_overlay.py`、`window.py`、QTextDocument、输入/删除/光标/滚动/IME 行为。`packaging/linux/source-baseline.sha256` 冻结了 8 个生产模块的字节哈希。

本轮新增：`packaging/OneLine.spec`、`packaging/linux/{Dockerfile,frozen_entry.py,requirements-runtime.txt,requirements-build.txt,source-baseline.sha256,README.md,dependency-notes.md}`、`packaging/LICENSE_NOTES.md`、`scripts/{build-linux.sh,smoke-linux-build.sh,kylin-system-check.sh}`、`.github/workflows/linux-x86_64-onedir.yml`、`docs/KYLIN_ACCEPTANCE_CHECKLIST.md`、`.dockerignore`；修改 `.gitignore` 以允许追踪 spec、忽略生成的依赖报告。

## 构建设计（尚未实际执行）

- Docker 容器：`quay.io/pypa/manylinux_2_28_x86_64:2026.05.07-2`，AlmaLinux 8 系 userspace，预期 glibc 2.28；GitHub runner 仅运行 Docker，不以 Ubuntu 系统库生成产物。
- Python：3.13.5，从官方源码校验 SHA256 后以 `--enable-shared` 构建；通用 x86-64 编译目标，不使用 `-march=native`。
- PyQt5：5.15.11；Qt 运行库包：5.15.19；PyQt5-sip：12.20.0。与已通过 Mac 门禁的版本一致。
- PyInstaller：6.15.0；hooks-contrib：2025.8。只做 onedir；spec 显式检查并纳入 `libqxcb.so` 与 `libqoffscreen.so`，无图标/数据资产，排除测试与开发缓存。
- 顺序：源码哈希检查 → `pip check` → Linux offscreen Release Gate → PyInstaller → `file`/关键 `ldd` → 真正的冻结二进制 offscreen smoke → tar.gz → SHA256 → Actions artifact 上传。任何一步失败即停止。

## 已完成的本机验证

- macOS 离屏 Release Gate：69 passed、2 skipped；此前 Cocoa Gate：71 passed（本轮未重复）。
- 源码模式的打包入口 smoke：`ONELINE_SMOKE_OK`，仅表明入口逻辑可构造窗口、Editor、Overlay 并插入合成文本，不是 Linux 冻结程序 smoke。
- 3 个 shell 脚本通过 `bash -n`；spec/入口通过 Python 语法检查；GitHub Actions YAML 可解析；8 个生产模块与哈希清单一致。
- `build-linux.sh` 在 macOS 上按设计拒绝运行，未交叉生成 Linux 程序。

## 未完成的 Phase 1 成功标准

本机没有 Docker。远端已确认存在；本机 Git HTTPS 缺少写入凭据，SSH 公钥也未获 GitHub 接受。GitHub 连接已具备推送权限。连接显示该仓库当前为公开，用户已明确允许将本阶段源码、测试和打包文件推送到该公开仓库。Actions 尚未触发，故**未在 Linux 容器运行 Release Gate、PyInstaller 或冻结程序 smoke**。尚无 `dependency-report.txt`、`dist/OneLine/`、tar.gz、SHA256 或可下载的 Actions artifact。`ldd libqxcb.so` 与目标麒麟兼容性均未验证。不能将前述配置与 Mac 检查报告为“Artifact 已准备好”。

## 风险与下一步

1. 通过已连接的 GitHub 权限上传已审查的候选提交到远端默认分支，以便手动触发 `workflow_dispatch`；远端现有提交和 `LICENSE` 必须保留。创建明确的 RC tag/branch。
2. 手动触发工作流，检查容器构建、Python shared library、依赖解析、Release Gate、PyInstaller、`ldd`、冻结 smoke、SHA256 与 artifact 下载。若失败先区分 packaging 与 application 问题，不修改编辑核心掩盖故障。
3. 记录运行中的容器 image ID、实际 glibc、tar.gz 大小及 SHA256。镜像目前固定 tag 而非 digest，后续需固定不可变 digest。
4. 将 artifact 转到银河麒麟 V10 兆芯 x86-64 实机，先运行只读环境检查，再按 `docs/KYLIN_ACCEPTANCE_CHECKLIST.md` 验收 X11/XWayland、Qt 插件、中文 IME、文件与 Session。
5. 正式发行前完成 `packaging/LICENSE_NOTES.md` 所列许可核对；本阶段不作法律结论。

构建 userspace 选择参考 [manylinux 官方说明](https://github.com/pypa/manylinux)；PyInstaller 官方指出 Linux 上不捆绑 glibc，应在足够旧的系统构建：[Linux 兼容性说明](https://pyinstaller.org/en/stable/usage.html)。银河麒麟 V10 的实际子版本/架构仍须现场核实；[麒麟桌面 V10 SP1 官方发布说明](https://www.kylinos.cn/upload/1/kycms/20250610/1932360363166240768.pdf)列出了相关 glibc 版本，不能替代目标机器检查。
