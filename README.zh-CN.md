<div align="center">

# scholar-cards

**把你的被引次数、h 指数和高被引论文做成卡片，放到个人主页或 GitHub 主页，并由 GitHub Action 定时更新。** 数据来自
[OpenAlex](https://openalex.org)（开放数据，无需注册），每个数字都能追溯到对应的 API 记录；卡片是自包含的 SVG，可以是亮色、暗色，或跟随读者的系统设置。

<a href="https://github.com/zch6a/scholar-cards/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/zch6a/scholar-cards/actions/workflows/ci.yml/badge.svg"></a>
<img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-blue">
<img alt="No dependencies" src="https://img.shields.io/badge/dependencies-none-2ea44f">
<a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-blue"></a>

[English](README.md) · **简体中文**

</div>

---

GitHub 主页有统计卡片；学者主页（al-folio、academicpages、Hugo Academic）上的被引数却是手动填的，常常过时好几个月。
scholar-cards 从你的 OpenAlex 记录生成卡片，定时工作流让它们保持最新。

<p align="center">
  <img alt="一位虚构学者的统计卡片：总被引 6,088，h 指数 27，i10 指数 48，论文 99 篇" src="docs/zh/stats.svg">
  <img alt="虚构学者的高被引论文" src="docs/works.svg">
  <img alt="虚构学者的逐年被引，当年标为截至目前" src="docs/citations.svg">
</p>

<sub>虚构的学者（[examples/scholar.json](examples/scholar.json)）；你的数据来自 OpenAlex。</sub>

## 用法

```bash
uvx --from git+https://github.com/zch6a/scholar-cards scholar-cards search "Your Name"
```

列出 OpenAlex 里这个名字对应的作者记录（ID、ORCID、机构、论文数与被引数）。OpenAlex 有时会把一个人拆成几条记录：选带你 ORCID 的那条，
或者最大的那条；工具不会替你挑。然后：

```bash
scholar-cards A5023888391 -o cards/          # 或者你的 ORCID：0000-0002-1825-009X
```

会写出 `cards/stats.svg`、`cards/works.svg`、`cards/citations.svg` 和 `cards/scholar.json`（数字、日期，以及数据来源的 API 地址）。放进页面：

```markdown
![我的被引](cards/stats.svg)
```

`--theme auto` 跟随读者的系统配色。如果要跟随读者在 GitHub 上选的主题，两种都生成（`--theme light,dark`），让 GitHub 来选：

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="cards/stats-dark.svg">
  <img alt="我的被引" src="cards/stats-light.svg">
</picture>
```

| 选项 | |
|---|---|
| `--cards stats,works,citations` | 生成哪些卡片（默认三张都要） |
| `--theme auto\|light\|dark` | `auto` 跟随读者的配色；`light,dark` 两种都写（`stats-light.svg`、`stats-dark.svg`） |
| `--lang en\|zh` | 卡片上的文字 |
| `--top N` | 高被引论文卡上的论文数（默认 5） |
| `--snapshot scholar.json` | 从快照重新生成，不联网 |

不需要 API key：一份主页只要两次请求。在 `OPENALEX_API_KEY` 里放一个 OpenAlex 的免费 key 可以提高每日额度；它只放在请求头里，
不会出现在 URL 中，也不会写进快照。

## 用 GitHub Action 定时更新

在你的主页仓库里建 `.github/workflows/scholar-cards.yml`：

```yaml
on:
  schedule: [{ cron: "0 6 * * 1" }]   # 每周一
  workflow_dispatch:
permissions:
  contents: read
concurrency: scholar-cards             # 同一时间只跑一个：手动运行不会和每周的那次冲突
jobs:
  cards:                               # 用只读权限取数并生成卡片
    runs-on: ubuntu-latest
    steps:
      - uses: zch6a/scholar-cards@v0
        with:
          author: A5023888391          # 或者你的 ORCID
          out: cards
      - uses: actions/upload-artifact@v4
        with: { name: cards, path: cards/ }
  commit:                              # 提交卡片；只运行 git
    needs: cards
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - run: rm -rf cards                # 不再生成的卡片（比如去掉了某个主题）也一并删掉
      - uses: actions/download-artifact@v4
        with: { name: cards, path: cards/ }
      - run: |
          git add -A cards
          git diff --cached --quiet && exit 0
          git -c user.name=scholar-cards -c user.email=actions@users.noreply.github.com commit -m "Update scholar cards"
          git push
```

能写你仓库的那个任务不运行本工具的任何代码；运行本工具的任务没有写权限。改了 `out` 的话，提交任务里的 `cards/` 路径也要一起改。每次运行通常都会产生一次提交：卡片上的日期会变。如果你的仓库要求，把 action 固定到具体提交。
用 al-folio 或 academicpages 时，把 `out` 指向网站会发布的一个专用目录（例如 `assets/img/scholar-cards/`，不要用 `assets/img/` 本身：提交任务每次运行都会清空这个目录），把卡片当图片用。工作流推送的提交不会触发其他工作流，所以靠推送部署的网站（al-folio 就是）要等下次部署才会发布新卡片；想立刻部署，在提交任务里加上 `gh workflow run <你的部署工作流>`，并给它 `actions: write` 权限。al-folio 自带的暗色开关不会改变读者的系统设置，所以在那里用与网站一致的 `theme: light` 或 `dark` 比 `auto` 更合适。

## 谁引用了一篇论文、怎么说的：`scholar-cards cited`

引用数只说明有多少；`cited` 说明是谁、用什么话引用的。它列出引用某篇论文（arXiv 编号、DOI 或 Semantic Scholar 编号）的论文，最新的在前，附上引用它的句子，数据来自 Semantic Scholar 的公开 API（只发送这篇论文的编号）。加 `--new` 时，它把已经见过的引用论文记在一个状态文件里，只列新的，方便每周的工作流开 issue。

```console
$ scholar-cards cited arXiv:2312.00752 --limit 1000
Mamba: Linear-Time Sequence Modeling with Selective State Spaces: 1000 citing paper(s) of 10,263 counted by Semantic Scholar
  with the sentences that cite it: 759; contrasts with 98, compares with 62, builds on 227, mentions 1086; claims to beat it: 0
...
2026-10-08  [builds on]       MemReg: Streaming Outdoor LiDAR Point Cloud Registration with Hybrid Memory Buffers
            “In this paper, we adopt the vanilla Mamba architecture [34] in our temporal encoding layer as illustrated in Fig.”  (builds on: we adopt)
2026-09-01  [contrasts with]  Towards Efficient and Effective Unimodal Trajectory Representation Learning: A Simple Yet Powerful Approach · IJCAI/ECAI
            “Although current Mamba [Gu and Dao, 2023] architectures offer linear complexity, since standard SSMs are inherently causal, this architecture fails to capture the non-causal topological dependencies intrinsic to road networks.”  (contrasts with: Although)
```

每个句子按词语规则加一个标签，并显示起决定作用的词：**builds on**（“we adopt”、“based on”、“follows”、“backbone”）、**compares with**（“baseline”、“outperforms”、“we compare”、带 ± 的结果）、**contrasts with**（“however”、“although”、“fails to”、“lacks”），或 **mentions**。这些只是提示，不是判断：随机抽取 40 个引用 Mamba 的句子人工阅读，标签与阅读结果一致的有 27 个（builds on 10 个中 6 个，contrasts with 4 个中 1 个，compares with 1 个中 1 个，mentions 25 个中 19 个）；“whereas”、“unlike” 常常只是描述，并非反对。第一版效果更差（在另一组样本上 40 个中 25 个），规则就是据此修正的：“rather than” 被当成比较，“follows”、“as in” 没有识别，“Gu et al. proposed...” 被当成引用者自己的说法。引用论文以自己的口吻说优于被引论文时，列为 “claims to beat it”。

Semantic Scholar 只对部分引用论文有引用句（Mamba 的前 1000 篇引用中有 759 篇），而且公开 API 经常繁忙：`cited` 会等待后重试（5、20、60、120 秒），在 `S2_API_KEY` 里设置免费的 key 会稳定很多。`--format markdown` 输出可用于 issue 的表格，`--format json` 输出全部内容。

```yaml
# .github/workflows/cited.yml: every Monday, an issue listing the week's new citations of your paper
on:
  schedule: [{cron: "0 7 * * 1"}]
  workflow_dispatch:
permissions:
  contents: write   # to commit the state file (the citing papers already seen)
  issues: write
jobs:
  cited:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2 # v10.3.3
      - env:
          GH_TOKEN: ${{ github.token }}
          S2_API_KEY: ${{ secrets.S2_API_KEY }}   # optional
        run: |
          if ! uvx --from git+https://github.com/zch6a/scholar-cards@v0 scholar-cards cited arXiv:2312.00752 \
               --new --state cited/state.json --format markdown --fail-on-new > news.md; then
            gh issue create --title "New citations" --body-file news.md
          fi
          git config user.name github-actions; git config user.email github-actions@users.noreply.github.com
          git add cited/state.json && git commit -m "cited: state" && git push || true
```

## 这些数字是什么

| | |
|---|---|
| 总被引、论文数 | OpenAlex 对这条作者记录的统计 |
| h 指数、i10 指数、近两年篇均被引 | OpenAlex 的 `summary_stats` |
| 逐年被引 | OpenAlex 的 `counts_by_year`（最近十年）；当年淡化并标为“截至目前” |
| 高被引论文 | 作者的论文按被引排序，附期刊/会议与年份 |

它们和 Google Scholar（收录来源更多，其中有些不是论文）、Scopus 的数字不同。卡片上写明了“OpenAlex”和日期；`scholar.json` 里有确切的 API 地址。

## 局限

- 数字就是 OpenAlex 的：作者记录被拆分或合并、论文归错了人，卡片上会原样显示。到 OpenAlex 更正（它接受更正），下次运行就会更新。
- 一张卡片对应一条作者记录；拆成多个 ID 的记录不会被加总。
- OpenAlex 自己的数据有错：搜索可能返回一条名字是好几个人的记录，ORCID 也可能指到别人的记录。工具会打印取到的是谁，记录里的 ORCID 与你给的不一致时会警告。

## 同一套工具

[paper-proof](https://github.com/zch6a/paper-proof) 检查论文的参考文献与数字；[submit-check](https://github.com/zch6a/submit-check) 按会议规则检查论文；
[arxiv-diff](https://github.com/zch6a/arxiv-diff) 显示版本之间改了什么；[exp-tables](https://github.com/zch6a/exp-tables) 把实验结果变成只在有依据时才加粗的表格。

## 属于 research-kit

这是 13 个开源科研工具之一，覆盖从读论文到论文发表之后。全部工具按科研流程的介绍，以及安装它们技能的 Claude Code 插件市场，见 [research-kit](https://github.com/zch6a/research-kit) · [网站](https://zch6a.github.io/research-kit/)。

## 许可证

MIT
