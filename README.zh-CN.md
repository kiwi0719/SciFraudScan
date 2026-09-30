# SciFraudScan

[English](README.md) | **简体中文**

[![CI](https://github.com/kiwi0719/SciFraudScan/actions/workflows/ci.yml/badge.svg)](https://github.com/kiwi0719/SciFraudScan/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](requirements.txt)
[![Agent Skill](https://img.shields.io/badge/Agent_Skill-SKILL.md-8A2BE2.svg)](SKILL.md)
[![Release](https://img.shields.io/github/v/tag/kiwi0719/SciFraudScan?label=release)](https://github.com/kiwi0719/SciFraudScan/tags)

**为科研数据和论文报告的统计量找异常信号，从不下结论。**

SciFraudScan 是一个给 Claude 用的 [Agent Skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)，
同时也是一个普通的 Python 命令行工具。它检查科研数据和论文里印出来的数字：
不可能存在的均值和标准差、和检验统计量对不上的 p 值、重复或派生出来的列、
尾数偏好、好得不正常的基线平衡，以及一批文献中的 p-hacking 痕迹。

每一项检查给出的都是**需要进一步核查的线索**，不构成对任何人的学术不端指控。
`SKILL.md` 会要求 Claude 按这个口径报告结果。

## 目录

- [状态](#状态)
- [安装](#安装)
- [快速体验](#快速体验)
- [检查项](#检查项)
- [基准测试](#基准测试)
- [局限](#局限)
- [文档](#文档)
- [参与贡献](#参与贡献)

## 状态

| | |
|---|---|
| 版本 | `v0.5.0`（[更新日志](CHANGELOG.md)） |
| 运行方式 | Claude Agent Skill（Claude Code、Claude.ai、Agent SDK）；独立命令行 |
| 依赖 | Python 3.10+、numpy、pandas、scipy；读 `.xlsx` 时另需 openpyxl |
| 默认启用（已验证） | GRIM、GRIMMER、报告 p 值重算、基线 p 值可达性 |
| 生产使用 | 仅用于初筛。每个 flag 都必须由人对照原文核实 |

## 安装

### 作为 Claude skill

Claude Code（个人 skills 目录；想随仓库共享就放到项目里的 `.claude/skills/`）：

```bash
git clone https://github.com/kiwi0719/SciFraudScan ~/.claude/skills/scifraudscan
pip install -r ~/.claude/skills/scifraudscan/requirements.txt
```

目录名必须是 `scifraudscan`，与 `SKILL.md` 里的 `name:` 一致。当你让 Claude
检查一篇论文、一张表或一个数据集时，它会自动加载这个 skill；也可以用
`/scifraudscan` 直接调用。

Claude.ai：把仓库目录打成 zip，在 *Settings → Capabilities → Skills* 上传。

### 作为命令行工具

```bash
git clone https://github.com/kiwi0719/SciFraudScan && cd SciFraudScan
pip install -r requirements.txt
python scripts/scan.py --help
```

## 快速体验

```bash
python scripts/scan.py examples/fabricated_trial.csv \
  --group-column arm --time-column enrol_day \
  --reported-stats examples/reported_stats.csv \
  --p-values examples/p_values.csv --experimental
```

每份报告都带着生成它的版本号，任何一条发现都能追溯到具体版本。下面是在
`benchmarks/real_cases/` 里那篇已撤稿论文上的真实输出（工具输出本身是英文）：

```
$ python scripts/scan.py --reported-stats benchmarks/real_cases/sigirci_wansink_2015_regret/reported_stats.csv
SciFraudScan 0.5.0
============================================================

Input: 0 rows, 0 columns, 30 reported-statistic rows
Result: 2 flagged, 0 clear, 1 not applicable (highest severity: high)
Not run (input missing):
  - baseline_p: needs --baseline-summary

Reported statistics
------------------------------------------------------------
[FLAG] GRIM (high)
        10 of 30 reported means cannot arise from N responses on the stated scale.
          ...
[FLAG] SD Feasibility (GRIMMER / variance bounds) (high)
        8 of 20 testable mean/SD pairs are impossible; an SD is testable only
        where the mean itself is attainable.
          ...
[n/a]  Reported p-value Consistency
        No row supplied a test statistic with its df (or, for Mann-Whitney U,
        its group sizes) and a reported p-value.
```

输入文件可以是 `.csv`、`.tsv` 或 `.xlsx`。`--format json` 输出同样的结果的结构化版本，
Claude 读的就是这个。

## 检查项

| 组 | 检查 |
|---|---|
| `reported_stats` | GRIM、GRIMMER 及方差上下界、p 值重算 |
| `authenticity` | Benford 首位数字、尾数偏好、重复增量 |
| `duplication` | 完全重复与近似重复行、线性变换与置换重复、重复数值块 |
| `structure` | 恒定差值、恒定比值、近乎完美的相关、过度规则 |
| `randomization` | Carlisle 基线平衡（双侧检验与"过于平衡"检验） |
| `covariance` | 近共线的列对、近奇异的协方差矩阵 |
| `timeseries` | 序列自相关、频谱周期性 |
| `pvalues` | Caliper 检验、p-curve 形态、显著性过多 |
| `baseline_p` | 基线表里印出的每个 p 值，能否由表中的 n / 均值 / SD 算出来 |
| `baseline_balance` | 已发表基线表的 Carlisle 平衡性，对照经验参考分布 |

报告统计量类检查不需要原始数据，只要论文里印出来的数字；也只有它们能证明
一个结果是*不可能*的，而不仅仅是不寻常。

## 两层检查

默认运行的是行为经过实测的检查，其余的需要显式开启。

| | 默认 | `--experimental` |
|---|---|---|
| 检查 | GRIM、GRIMMER、报告 p 值一致性（t / F / χ² / r / Mann-Whitney U）、基线 p 值可达性 | 数字、重复、结构、协方差、序列、p-curve、基线平衡 |
| 用真实已发表案例验证过 | 是，逐格核对 | 否 |
| 真实数据上的误报率 | 7,307 个案例上 **0.00%** | 无法用同样方法测量；**75%** 的普通数据集至少触发一个 |

每个实验性 flag 都会打印该检查在普通真实数据上的触发率，因为没有基础率的
严重程度毫无意义。

用真实数据重新校准后，三项实验性检查的触发率大幅下降：尾数偏好 87% → 8%、
Benford 74% → 0%、协方差结构 57% → 0%；另有两项仍分别在 43% 和 45%，作为
flag 依然没用。这些数字是在校准过程之外留出的 150 个数据集上测得的。修了
什么、没修什么、灵敏度付出了什么代价，见
[`benchmarks/false_positives/`](benchmarks/false_positives/)。

## 没有风险总分

每项检查只返回 `flag`、`clear` 或 `not_applicable`，并附上背后的数字。没有
0-100 的总分：对各项检查取平均会让通过的检查稀释真正的发现，还会暗示一种
并不存在的校准。[`references/METHODOLOGY.zh-CN.md`](references/METHODOLOGY.zh-CN.md)
说明了每项检查的假设、最少数据量、阈值和失效情形，引用任何结果之前请先读它。

## 基准测试

`examples/clean_trial.csv` 是诚实生成的；`examples/fabricated_trial.csv`
是同一个试验被植入五处缺陷后的版本。

| | 诚实数据 | 伪造数据 |
|---|---|---|
| flagged | **0** | 12 |
| clear | 15 | 9 |
| not applicable | 1 | 1 |

两者都用 `--experimental --group-column arm --time-column enrol_day` 运行；
伪造数据那次还额外传入 `examples/reported_stats.csv` 和
`examples/p_values.csv`，12 个 flag 中有 6 个来自它们。

```bash
pytest                                   # 已作为回归测试包含在内
python benchmarks/generate_examples.py   # 用固定种子重新生成
```

这说明这些检查能在它们声称能发现的问题上触发，而在形状相同的诚实数据上保持安静。

### 误报率

测误报率通常需要已知可靠的数据。这里换了个办法：拿真实原始数据，自己算出
汇总统计量，按论文的方式取整；这样一来，任何 flag 都是**可证明的**误报。

| 检查 | 案例数 | 误报 |
|---|---|---|
| GRIM | 2674 | **0** |
| GRIMMER | 2674 | **0** |
| 报告 p 值（Student t） | 653 | **0** |
| 报告 p 值（Mann-Whitney U） | 653 | **0** |
| 基线 p 值可达性 | 653 | **0** |

数据来自 [Rdatasets](https://vincentarelbundock.github.io/Rdatasets/) 的 300 多个
真实数据集。降到零之前，这次测量发现并修复了两个问题：一个取整约定让 GRIM
拒绝了本可达到的均值，以及 ~1e13 以上的浮点精度损失。见
[`benchmarks/false_positives/`](benchmarks/false_positives/)。

### 与独立实现的一致性

GRIM 与 R 参考实现 **scrutiny 0.6.1** 在 **6000/6000** 个案例上一致。GRIMMER
是较弱的一侧：scrutiny 多拒绝 2.6% 的组合，而不存在本工具拒绝、scrutiny 不
拒绝的情况。**如果需要完整强度的 GRIMMER，请用 scrutiny。** 见
[`benchmarks/crosscheck/`](benchmarks/crosscheck/)。

### 真实已发表案例

`benchmarks/real_cases/` 用真实论文验证报告统计量类检查。这些论文的数字已经
在同行评议文献中被重新分析过，这里逐格对照那些再分析得出的结论：

| 案例 | 状态 | 检查内容 | 结果 |
|---|---|---|---|
| Sigirci & Wansink (2015), *BMC Nutrition* | 2017 年**撤稿** | GRIM / GRIMMER，30 个均值 + 20 个 SD | 30/30、20/20 与已发表结论一致 |
| Just, Sigirci & Wansink (2014), *J Sensory Studies* | 2017 年更正 | GRIM / GRIMMER，28 格 | 28/28 与已发表结论一致 |
| Sato / Iwamoto 系列试验 | **撤稿**（20 余篇） | 基线表，50 个变量 | 10 个印出的 p 值中 5 个不可达；平衡检验**没有触发** |
| 匿名，未识别 | **未知** | 30 个 Mann-Whitney 比较 | 30 个中 29 个内部一致，*不是*误报对照，见下文 |

Wansink 相关结论来自 [van der Zee, Anaya & Brown (2017)](https://doi.org/10.1186/s40795-017-0167-x)，
并与再分析作者的[代码仓库](https://github.com/OmnesRes/pizzapizza)交叉核对。
Sato/Iwamoto 基线数据是 Mark Bolland 以 MIT 许可发布的
[reappraised](https://cran.r-project.org/package=reappraised) 包中的
`SI_pvals_cont` 数据集。这些格子里约有一半是*不*应被标记的值，所以误报一侧
同样被测到了。每个案例的 `SOURCE.md` 记录了 DOI、编辑部处理结果和每个数字的出处。

**Sato 案例包含一个阴性结果，并且保留了它。** 在这 50 个基线变量上，平衡检验
返回 `clear`（平均 p = 0.567，真实已发表试验为 0.516；蒙特卡洛 p = 0.13）。
10% 的样本太小，检验没有功效。没有为了让它触发而调整任何阈值；这个案例是由
不对分布做任何假设的 p 值可达性检查发现的。

追查这个阴性结果时发现了一个更严重的问题，现已修复：**即使试验是诚实的，由
已发表的、取整后的汇总统计量算出的基线 p 值也不服从均匀分布。** 在 Carlisle
收集的 29,789 个真实基线变量中，13.1% 大于 0.95，而均匀零假设下应为 5%。
按均匀分布检验时，诚实的 500 变量集合**100%** 会被标记。现在改为与该经验分布
比较，误报率保持在 1% 左右，同时仍能在 99% 的情况下发现真正过于平衡的集合。
见 [`scripts/scifraudscan/reference/README.md`](scripts/scifraudscan/reference/README.md)。

匿名案例没有独立结论，所以不能说明检查是准确的：只有在"通过"本身已知正确时，
"这些行通过了"才算证据。它只是把真实输入上的行为固定下来，仅此而已。

**clear 不等于放心。** 这些检查只测报告的数字彼此之间在算术上是否一致。经过
软件处理的伪造数据本身就是一致的，会通过所有检查。

适用面仍然很窄：算术类检查只在来自两个课题组的三个真实案例上验证过。重复、
尾数偏好和序列类检查没有真实案例验证，也没有通用的误报率。

## 局限

只给筛查信号。不做图像取证，不查文字和参考文献，没有完整的 SPRITE 搜索。
p 值类检查需要一批结果，而不是单篇研究。大约 22 项检查在未做多重比较校正的
情况下运行，所以诚实数据上出现一些 flag 是预期之中的；严重程度和每项检查的
失效情形远比数量重要。

## 文档

- [`SKILL.md`](SKILL.md)：Claude 收到的指令，包括如何撰写结果（英文，供模型读取）
- [`references/METHODOLOGY.zh-CN.md`](references/METHODOLOGY.zh-CN.md)（[English](references/METHODOLOGY.md)）：
  每项检查的假设、最少数据量、阈值和失效情形
- [`benchmarks/`](benchmarks/)：真实案例、误报率测量、与 scrutiny 的交叉核对（英文）
- [`CHANGELOG.md`](CHANGELOG.md)

## 参与贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。简单说：`make check` 必须全绿；任何让
`examples/clean_trial.csv` 出现 flag 的改动都是错的。安全问题按
[SECURITY.md](SECURITY.md) 私下报告；社区行为遵循
[Contributor Covenant](CODE_OF_CONDUCT.md)。

## 引用

元数据见 `CITATION.cff`。如果在发表的工作中使用了它，请同时引用原始方法，
这些方法及其出处都列在 [`references/METHODOLOGY.zh-CN.md`](references/METHODOLOGY.zh-CN.md)
里。本工具只是别人统计方法的一个实现。

## 许可证

[MIT](LICENSE)
