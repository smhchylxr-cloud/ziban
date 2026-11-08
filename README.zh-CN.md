# ziban

**给"浏览器之外"的一切，做对中文断行。**

[English →](README.md)

浏览器很多年前就有了 `text-spacing-trim`、`line-break: strict` 和真正的禁则处理。
但除了浏览器，别的地方全都得自己重写一遍——Pillow、ReportLab、SVG、ffmpeg 烧字幕、
`python-pptx`、canvas——而且几乎都写错了，因为**没有一个地方可以去问**。

`ziban` 就是那个地方：一个纯 Python 的中文排版引擎，把「一段文字 + 一个盒子」
变成排版师认可的若干行，并且在每次不得不妥协时，给出机器可读的说明。

## 八秒钟看懂问题

`if len(s) > N: cut()` 的结果：

```
他说：「这次不一样。
」然后关掉了对话框。
```

`ziban`：

```
他说：「这次不一样。」
然后关掉了对话框。
```

第一行以 `」` 开头。这不是审美问题：[《中文排版需求》(CLREQ)](https://www.w3.org/TR/clreq/)
明确规定收尾标点不可出现在行首（避头）、起首标点不可出现在行尾（避尾）。
所有非浏览器的渲染器都在默默违反这条规则——而它违反的，恰恰是读者一眼就能看见的那些标点。

## 安装

```bash
pip install ziban              # 核心，零依赖
pip install "ziban[pillow]"    # 需要用真实字体度量时
```

Python 3.9+。不要浏览器、不要编译、不要 ICU、不要模型。

## 用法

### 命令行

```console
$ echo "这是一个比较长的段落，用来看断行在真实文本上的表现。" \
    | ziban wrap - --width-em 8 --ruler
      +----------------+
  1   | 这是一个比较长的 |   8.0em
  2   | 段落，用来看断行 |   8.0em
  3   | 在真实文本上的表 |   8.0em
  4   | 现。             |   2.0em

4 line(s), box 8.0em, no diagnostics
```

行号后面那一列：`>` 表示本行末尾有标点悬挂，`<` 表示有标点挤压，`!` 表示溢出。
加 `--json` 得到结构化结果，给脚本和 agent 用。

### 库

```python
from ziban import Style, layout, EmMetrics

page = layout(
    "他说：「这次不一样。」然后关掉了对话框。",
    width=10 * 32,                     # 一行 10 个字
    style=Style(size=32, leading=1.7),
    metrics=EmMetrics(32),             # 或 PillowMetrics("NotoSerifSC.otf", 32)
)

for line in page.lines:
    print(line.text, line.width)

page.diagnostics
# [Diagnostic(code='ORPHAN_LINE', line=1, ...)]
```

每一行都带着自己的解释：

```python
line.adjustments   # (Adjustment(kind='hang', index=10, delta=32.0),)
line.slack         # 剩余空间
line.overflow      # 超出盒子的像素，放得下就是 0
line.justify_spacing
```

## 它做了什么

| | |
|---|---|
| **避头尾** | 收尾标点不进行首，起首标点不留行尾 |
| **标点挤压** | 差一点点放得下时，全角标点压到半宽 |
| **行末悬挂** | 宁可让标点悬出边界，也不把它挤到下一行；上限 1 em，且不超过行宽的 1/4 |
| **中西混排** | 汉字与拉丁文之间可断，拉丁单词内部不断，数字不与单位分家 |
| **硬断行** | `\n` 一定生效，空行保留 |
| **诊断** | `OVERFLOW`、`NO_BREAK_OPPORTUNITY`、`KINSOKU_FALLBACK`、`ORPHAN_LINE`，每条都带修复建议 |
| **确定性** | 同文本 + 同字体 + 同字号 → 逐字节相同的输出，跨平台一致 |

## 它不做什么

- 不调 AI，不要 API key，不做"帮我写文案"。
- 不要浏览器、不要无头 Chromium、不要装排版引擎。
- 不做 GUI 编辑器。
- 不自动发布到任何平台。
- **不打包任何字体。** 微软雅黑、苹方都不能随包分发；要么自带，要么用思源黑体/Noto（OFL）。

最后一条不是洁癖：一个内置专有字体的库，公司是不能用的。

## 规则是数据，不是 if-else

所有排版策略都在 [`src/ziban/data/clreq.toml`](src/ziban/data/clreq.toml) 里：

```toml
[kinsoku]
head_forbidden = "　，、。．；：？！）〕〉》」』】”’｝…"
tail_forbidden = "（〔〈《「『【“‘｛"

[compress]
compressed_ratio = 0.5
chars = "，、。．；：？！）〕〉》」』】”’…"

[hang]
max_ratio = 1.0
max_share = 0.25
```

改行为就改这张表。日文规则集是第二个 TOML，不是第二个引擎。这也是为什么贡献很便宜：
**绝大多数排版 bug 只值一行数据。**

## 和它们比

| | 禁则 | 挤压 | 悬挂 | 浏览器之外可用 | 确定性 |
|---|---|---|---|---|---|
| [heti](https://github.com/sivan/heti) | 靠浏览器 | 部分 | ✗ | ✗ | ✗ |
| [pangu.py](https://github.com/vinta/pangu.py) | ✗ | ✗ | ✗ | ✓ | ✓ |
| [budoux](https://github.com/google/budoux) | ✗ | ✗ | ✗ | ✓ | ✓ |
| 浏览器 `text-spacing-trim` | ✓ | ✓ | 部分 | ✗ | ✓ |
| **ziban** | ✓ | ✓ | ✓ | ✓ | ✓ |

`budoux` 决定"断在哪里语义上说得过去"，`ziban` 决定"这个断点排版上合不合法"。两者可以叠加。

## 状态

`0.1.0` —— 横排引擎完成，958 个测试全绿（24 段语料 × 6 种行宽 × 6 条不变量，
外加金标用例）。尚未发布到 PyPI。

接下来：

- **0.2** 跨平台字体探测；连续标点挤压（「。」占一个 em）；Knuth–Plass 式代价断行，
  让最后一行不再孤零零
- **0.3** 适配器：ReportLab、SVG、`python-pptx`；竖排放到开关后面
- **0.4** `cards` 示例：真正渲染 1080×1440 组图；再包一层 `SKILL.md` 让 agent 能调用

## 许可

MIT，见 [LICENSE](LICENSE)。

规则集依照 [CLREQ](https://www.w3.org/TR/clreq/)（W3C）；字符分类是
[UAX #14](https://www.unicode.org/reports/tr14/) 的裁剪子集。
