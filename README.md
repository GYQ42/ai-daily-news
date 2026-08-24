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

## 可选功能（不配置自动跳过）

### 📧 每天邮件推送日报
在 Secrets 里添加以下 6 个（SMTP 授权码从邮箱服务商获取，QQ / 163 / Gmail 均支持）：

| Secret | 说明 | 示例 |
| --- | --- | --- |
| `SMTP_SERVER` | 邮箱 SMTP 服务器 | `smtp.qq.com` / `smtp.163.com` |
| `SMTP_PORT` | 端口 | `465` |
| `SMTP_USERNAME` | 邮箱账号 | `xxx@qq.com` |
| `SMTP_PASSWORD` | SMTP 授权码（不是登录密码） | `xxxx` |
| `MAIL_TO` | 收件邮箱 | `xxx@qq.com` |
| `MAIL_FROM` | 发件人 | `AI日报 <xxx@qq.com>` |

配置后每天生成日报时会自动把 Markdown 附件发到你的邮箱。

### 🏠 自动更新到你的 GitHub 主页
想让日报同时出现在 `username.github.io` 主页仓库里，新建一个 PAT（Settings → Developer settings → Personal access tokens，勾选 `repo` 权限），然后添加：

| Secret | 说明 | 示例 |
| --- | --- | --- |
| `HOME_REPO` | 你的主页仓库 | `你的用户名/你的用户名.github.io` |
| `HOME_TOKEN` | PAT | `ghp_xxxx` |

配置后每天会自动把 `ai-daily/日期.md` 提交到主页仓库的 `ai-daily/` 目录，可通过 `https://你的用户名.github.io/ai-daily/` 访问。

### 🆓 不用自己的 API Key：免费 AI 方案
> ⚠️ 注意：GitHub Models 已于 2026-07-30 退役（见 [GitHub 文档](https://docs.github.com/zh/github-models)），推理 API 不再可用，本项目已移除该回退。

免费/低成本方案均兼容 OpenAI 接口，只需配置 3 个 Secret：

| Secret | 智谱 BigModel（推荐，glm-4-flash 有免费档） | DeepSeek（很便宜） | OpenAI |
| --- | --- | --- | --- |
| `LLM_API_KEY` | 在 [open.bigmodel.cn](https://open.bigmodel.cn) 创建 | [platform.deepseek.com](https://platform.deepseek.com) 创建 | [platform.openai.com](https://platform.openai.com) 创建 |
| `LLM_BASE_URL` | `https://open.bigmodel.cn/api/paas/v4` | `https://api.deepseek.com/v1` | `https://api.openai.com/v1` |
| `LLM_MODEL` | `glm-4-flash` | `deepseek-chat` | `gpt-4o-mini` |

AI 调用优先级：`LLM_API_KEY` > 内置词表。什么都不配也完全可以跑（内置词表模式）。
## 修改触发时间## 修改触发时间

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
