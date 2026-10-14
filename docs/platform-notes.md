# 平台兼容性准备（阶段三）

当前发布测试默认在 Intel Mac 的 PyQt5/Qt 5.15 离屏环境运行；长行 Session 恢复后的光标可见性必须另在 macOS Cocoa 图形后端验证，因为离屏插件的滚动几何行为不同。银河麒麟 V10、兆芯 x86-64、X11、XWayland 与 Wayland 尚未实机验证，也尚未开始 Linux 打包。

| 范围 | 当前做法 | 后续实机检查 |
| --- | --- | --- |
| Qt 窗口类型、置顶 | 无边框窗口使用 Qt 标志；有系统托盘时使用 `Qt.Tool`，否则使用 `Qt.Window` 以保留任务栏入口 | 窗口管理器是否接受置顶、是否显示任务栏入口 |
| 拖动与宽度调整 | 优先调用 `QWindow.startSystemMove` / `startSystemResize`，不支持时使用现有鼠标拖动回退 | Wayland 下系统操作是否可用；窗口位置恢复是否被忽略 |
| 隐藏与恢复 | 有托盘时隐藏并从托盘恢复；无托盘时最小化 | 麒麟桌面是否提供 StatusNotifierItem 或 XEmbed 托盘 |
| 透明度 | 使用 Qt `QWidget.setWindowOpacity`，范围 75–100% | X11 是否有合成管理器；Wayland 是否忽略该属性 |
| 文件与设置路径 | `pathlib.Path`、`QSettings.UserScope`、`QStandardPaths.AppConfigLocation` | 普通用户权限下是否可写；便携目录只读时能否正常使用 |
| 字体 | 系统默认字体和 Qt 字体选择器；指定字体缺失时交给 Qt 回退 | 中文字形、字号、缩放比例和输入法候选框 |
| 快捷键 | Qt 窗口快捷键；macOS 增加 Command 组合键 | 桌面快捷键冲突；隐藏后是否通过托盘或任务栏顺利恢复 |

Qt 5.15 文档说明：窗口快捷键只在所属顶层窗口活动时触发；系统托盘应先检查可用性；系统级移动/缩放取决于平台；X11 透明度依赖合成管理器和窗口管理器支持。参考 [QShortcut](https://doc.qt.io/archives/qt-5.15/qshortcut.html)、[QSystemTrayIcon](https://doc.qt.io/archives/qt-5.15/qsystemtrayicon.html)、[QWindow](https://doc.qt.io/archives/qt-5.15/qwindow.html)、[QWidget](https://doc.qt.io/archives/qt-5.15/qwidget.html)。

进入 Linux 构建前仍需收集目标麒麟电脑的发行版、glibc、桌面会话类型及 Qt xcb 依赖信息，再选择兼容的构建环境。CI 构建成功不等于兆芯实机通过。
