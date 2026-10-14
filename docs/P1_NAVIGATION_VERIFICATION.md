# OneLine P1 Navigation Verification

2026-10-14，macOS Cocoa 专项诊断。仅增加调试入口，未修改 `editor.py`、`window.py` 或其他生产代码；未开始 Linux 打包。

## 运行方式

```bash
./scripts/run-p1-navigation-check.sh --variant both --automated
```

该入口调用正式 `main.create_application()` 和 `OneLineWindow`。A 保留现行导航路径；B 只在此诊断进程中拦截导航路径对 `ensureCursorVisible()` 的 Python 调用，不改仓库内生产实现。设置、Session、打开的 TXT 都在临时目录。日志和 `results.json` 只含光标、几何、滚动条及 Overlay 状态，不含正文。输出目录另有合成样本和导航前后截图。

真实人工对照可分别运行：

```bash
./scripts/run-p1-navigation-check.sh --variant A --source paste --sample B
./scripts/run-p1-navigation-check.sh --variant B --source paste --sample B
./scripts/run-p1-navigation-check.sh --variant A --source session --sample B
./scripts/run-p1-navigation-check.sh --variant B --source session --sample B
```

可选 `--source plain|open|blank`、`--sample A|B|C|D|E`、`--cursor-at middle`。A/B/C/D 分别是约 5 视觉行、约 10 视觉行、中文长句、英文长句；E 是 1000 字符额外压力样本。`paste` 使用 Qt 原生 `insertFromMimeData` 路径，不占用系统剪贴板。要验收真实 `⌘V`，使用 `--source blank`，从输出目录的 `samples/B.txt` 或 `samples/C.txt` 自行复制并粘贴。

每次打开新窗口，只把该次首次 Left、Right、Home、End 作为首次导航观察；关闭再重开可重置。控制台会输出导航前后状态。正常关闭时，如果窗口提示未保存，可选择“不保存”。

## 自动诊断结果

- Cocoa：A/B 合计 32 个场景，覆盖粘贴、`setPlainText`、打开 TXT、Session 恢复；包含立即导航、稳定后导航、中段光标、Home/End、连续左右移动及模拟 IME preedit。
- A/B 样本在此机器上分别形成 5 和 10 个视觉行；E 形成 36 行。
- 首次 Left/Right：滚动条变化均为 0；`ensureCursorVisible()` 调用均为 0；32 个场景的导航后光标均与 viewport 相交。
- 导航前后静态画面中，Left/Right 最大像素变化比例 0.00164；Home/End 的跨行变化符合目标位置变化，A/B 相同。
- 曾报告的 23 个滚动单位首跳未在这组 Cocoa 场景复现。当前 A/B 并未进入受限 `ensureCursorVisible()` 分支，因此不能证明删除它是安全的，也不能确认它是首跳根因。
- 离屏 Release Gate：69 通过、2 跳过；Cocoa Release Gate：71 通过。

结果文件：`/var/folders/vs/fzvv8hy16p379xfpywy8ksbr0000gn/T/oneline-p1-navigation-vpbme31g/results.json`。此目录位于系统临时区，可能被系统清理；可通过 `--output-dir` 指定保留位置。

## 真实 Mac 人眼验收

2026-10-14 用户确认：Variant A、Variant B 的动态观感均正常，未见明显首次导航跳动。按预定决策规则，现行 A 的体验正常，即使曾记录较大的 Qt 内部滚动单位变化，也不构成已确认的用户可见功能退化；无需修改 `ensureCursorVisible()`。

以下细项保留为后续发布前的人工检查清单；本次确认仅明确覆盖 A/B 观感，不推定每一项均已逐项完成：

对 A、B 分别观察是否出现突兀移动、光标消失、Overlay 露出相邻视觉行：

1. 中文拼音候选窗、连续中文输入及长中文 `⌘V` 粘贴后首次 Left/Right。
2. 连续 Left/Right、Home/End，以及 Session 恢复后的第一次导航。
3. 删除长句、删空立即重新输入；确认输入内容和光标均正常。
4. 深色模式与透明度设置下重复导航，确认遮罩颜色和相邻行裁剪。

静态截图和模拟 IME 不能替代候选窗的逐项人工检查；上述未逐项确认的项目仍应在正式发布前完成。

## 当前门禁结论

该导航问题由 P1 降为 P2：**“Qt 首次导航内部 viewport 追赶，当前未发现用户可见功能退化。”** `ensureCursorVisible()` 未确认为根因，生产代码保持不变。P0 = 0、P1 = 0；就此导航门禁而言，可以进入 Linux 麒麟打包阶段。此结论不等于已经开始打包，也不代替其余平台与人工发布验收。
