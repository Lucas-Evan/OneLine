# 银河麒麟 V10 x86-64 实机验收清单（Phase 1）

先确认设备为兆芯 x86-64、银河麒麟 V10，并运行只读的 `scripts/kylin-system-check.sh`，保存输出。记录系统版本、`glibc`、X11/XWayland 会话、DPI、字体、窗口管理器和输入法名称。核验 `OneLine-linux-x86_64.sha256` 后解压 tar.gz；不安装 Python/pip，不修改系统 Qt、glibc、loader 或全局 `LD_LIBRARY_PATH`。

## 启动与动态库

- [ ] `./OneLine/OneLine` 可直接启动、正常退出。
- [ ] 无 Qt platform plugin 错误；`platforms/libqxcb.so` 存在。
- [ ] `ldd ./OneLine/OneLine` 与 `ldd ./OneLine/_internal/PyQt5/Qt5/plugins/platforms/libqxcb.so` 无未解释的 `not found`。
- [ ] X11 或 XWayland 环境可运行；记录原生 Wayland 表现，但本阶段不要求通过。

## 窗口

- [ ] 始终是 56px 高的悬浮长条、无边框，宽度改变不改变高度。
- [ ] 始终置顶、拖动、调整宽度可用。
- [ ] Esc 隐藏、默认隐藏/恢复快捷键可用；无托盘时也能找回窗口。

## 显示

- [ ] 中文字体字形完整，DPI 缩放下行高/光标自然。
- [ ] Visual Line Overlay 仅显示当前视觉行，无相邻行漏出。
- [ ] 长逻辑行自动视觉折行、真实换行不变，文字垂直居中。
- [ ] 浅色/深色主题、透明度设置下遮罩和菜单正确。

## 文本编辑

- [ ] 中文输入法及候选窗位置、连续中文输入正常。
- [ ] 英文输入、Backspace/Delete、长按删除正常。
- [ ] 撤销/重做、复制/粘贴正常。
- [ ] Home/End、Left/Right、跨视觉行导航正常；Up/Down 按逻辑行移动。
- [ ] 长文本折行后删除、删空再输入，光标可见且无卡顿或吞字。

## 文件

- [ ] Open、Save、Save As 成功；关闭未保存文档出现保存/不保存/取消。
- [ ] UTF-8 和 UTF-8 BOM 文件打开与保存内容一致。
- [ ] LF/CRLF 真实换行结构保持。
- [ ] 文件被外部修改时，保存冲突提示明确且不覆盖外部版本。

## Session 与系统集成

- [ ] 正常退出与重新启动恢复窗口位置、宽度、光标和会话。
- [ ] 异常退出后恢复未保存内容，不覆盖已有 TXT。
- [ ] Session 写失败时显示非模态提示，编辑仍可继续。
- [ ] 托盘、置顶、剪贴板、菜单快捷键与窗口管理器行为正常。

## 故障记录

记录：发行物 SHA256、目标机系统检查输出、复现步骤、期望/实际、`QT_DEBUG_PLUGINS=1 ./OneLine/OneLine` 的插件诊断、`ldd libqxcb.so` 结果。诊断日志不要附用户正文、Token 或私有路径。先区分打包遗漏和应用逻辑问题；不要用 `sudo` 复制库或覆盖系统 glibc 来掩盖问题。
