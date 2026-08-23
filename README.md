# 📰 AI 每日日报（GitHub Actions 版）

每天自动收集 AI 新闻 → 生成中文日报 → 自动提交到仓库。
配置 LLM（OpenAI / DeepSeek 等任意 OpenAI 兼容接口）后，还会为每条新闻生成一句话摘要，并**解释新闻中出现的核心概念**。

## 目录结构

```
ai-daily-news/
├── .github/workflows/ai-daily.yml   # GitHub Actions 定时任务
├── scripts/daily_ai_news.py         # 抓新闻 + 概念解释 + 生成日报
├── requirements.txt
├── README.md
└── docs/
    ├── README.md                    # 日报存档索引（自动更新）
    └── ai-daily/2026-xx-xx.md       # 每日日报（自动生成）
```

## 快速开始（5 步）

1. **在 GitHub 新建仓库**，例如 `ai-daily-news`，选 **Public**
2. **把本目录所有文件推上去**（务必推到默认分支 main/master，定时任务只认默认分支）
3. **（推荐）配置 LLM**：仓库 → Settings → Secrets and variables → Actions → New repository secret，添加：

   | Secret 名 | 说明 | 示例 |
   | --- | --- | --- |
   | `LLM_API_KEY` | API Key（必填才启用 AI 摘要/概念解释） | `sk-xxxx` |
   | `LLM_BASE_URL` | 接口地址（可选，默认 OpenAI） | DeepSeek 用 `https://api.deepseek.com/v1` |
   | `LLM_MODEL` | 模型名（可选） | `gpt-4o-mini` / `deepseek-chat` |

   > 不配置也能跑：会用内置词表解释常见概念（LLM、RAG、智能体、Token 等），但新闻摘要取原文简介。
4. **手动测试**：Actions 标签页 → 选中 `AI 每日日报` → **Run workflow**
5. **等待自动运行**：从明天起每天北京时间 **05:00 左右** 自动生成（cron 为 UTC 21:00，GitHub 偶有延迟属正常）

## 查看日报

- 仓库内：`docs/ai-daily/` 下的 Markdown 文件，根目录 `docs/README.md` 是索引
- 想用浏览器看（结合 GitHub Pages）：Settings → Pages → Source 选 **Deploy from a branch** → main → **/docs** → Save
  之后访问 `https://<你的用户名>.github.io/ai-daily-news/`

## 修改触发时间

编辑 `.github/workflows/ai-daily.yml` 中的 `cron`（GitHub 用 UTC 时间）：

| 北京时间 | cron |
| --- | --- |
| 05:00（默认） | `0 21 * * *` |
| 06:30 | `30 22 * * *` |
| 08:00 | `0 0 * * *` |

格式：`分 时 日 月 周`，`*` 表示每天/每月/每周。

## 常见问题

- **跑失败了？** 看 Actions 页面的日志。多数是某个 RSS 源失效——脚本会自动跳过坏源，不影响整体。
- **想换/加新闻源？** 编辑 `scripts/daily_ai_news.py` 顶部的 `RSS_FEEDS` 字典。
- **想加邮件/Telegram/Discord 通知？** 在工作流里追加一个对应的 Action 步骤即可。
- **定时任务突然不跑了？** GitHub 会暂停 60 天无活动的仓库的定时任务，手动 Run workflow 一次即可恢复。
- **概念解释想更精准？** 设置 3 个 Secrets 后，LLM 会从当天新闻里自动提炼概念并解释，比词表回退好很多。
