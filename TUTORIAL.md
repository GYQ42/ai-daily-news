# 📖 AI 每日日报 · 超详细配置教程（从零到跑通）

本教程面向完全没接触过 GitHub Actions 的用户，每一步都给出「网页操作路径」和「命令行方式」两种做法。
跟着做完，你的日报会自动完成：**每天定时抓新闻 → AI 摘要 + 概念解释 → 生成 Markdown → 发邮件给你 → 同步到你的 GitHub 主页**。

---

## 一、这个项目是怎么工作的

```
GitHub Actions 定时任务（每天北京时间 05:00 触发）
        │
        ▼
Python 脚本（scripts/daily_ai_news.py）
  ① 抓取：RSS 科技媒体 + arXiv 论文 + Hacker News
  ② 去重排序：取最新 10 条
  ③ AI 摘要 + 概念解释（配了 Key 时；否则用内置词表）
        │
        ▼
生成 docs/ai-daily/2026-08-24.md 并自动 commit 到仓库
        │
        ├── 📧 发邮件（配置 SMTP 后自动启用）
        └── 🏠 同步到你的 GitHub 主页仓库（配置 HOME_REPO 后自动启用）
```

**全免费额度**：GitHub Actions 公开仓库不限分钟数；私有仓库每月 2000 分钟也足够（每天约 2 分钟 × 30 天 = 60 分钟）。

---

## 二、准备清单

| 需要的东西 | 用途 | 花费 |
| --- | --- | --- |
| GitHub 账号 | 建仓库、跑 Actions | 免费 |
| （可选）邮箱 | 收日报邮件 + 拿 SMTP 授权码 | 免费 |
| （可选）AI API Key | 摘要和概念解释 | 免费档或几分钱/天 |
| Git（本地可选） | 推送仓库 | 免费（[git-scm.com](https://git-scm.com)） |

> 什么都不配置也能跑：**内置词表**会给新闻标题自动匹配并解释常见 AI 概念（LLM、Token、RAG、智能体……），新闻摘要取原文简介。AI 只是锦上添花。

---

## 三、第一步：创建 GitHub 仓库

### 网页方式
1. 登录 GitHub → 右上角 **+** → **New repository**
2. 填写：
   - Repository name：`ai-daily-news`
   - **Public**（推荐。私有也没关系，只是不能开 Pages 网页展示）
   - 不要勾选 Add README / .gitignore / license（避免和本地文件冲突）
3. 点 **Create repository**

### 命令行方式（装了 gh CLI）
```bash
gh repo create ai-daily-news --public --clone
```

---

## 四、第二步：把项目文件推上去

### 方式 A：本地 git 推送（推荐，保留提交历史）
打开终端（Windows 用 Git Bash），执行：

```bash
cd D:/Desktop/新建文件夹/ai-daily-news
git remote add origin https://github.com/<你的用户名>/ai-daily-news.git
git branch -M main
git push -u origin main
```

### 方式 B：网页直接上传 zip
1. 用之前的 `ai-daily-news.zip` 解压出所有文件
2. 进入刚创建的仓库页面 → **Add file → Upload files**
3. 把 `.github`、`scripts`、`docs`、`README.md`、`requirements.txt`、`.gitignore` 全部拖进去
4. 填提交信息 → **Commit changes**

---

## 五、第三步：手动测试（强烈建议先做这一步）

1. 仓库页面 → **Actions** 标签
2. 左侧点 **AI 每日日报**
3. 右侧点 **Run workflow** → 绿色 **Run workflow** 按钮
4. 等待约 1~2 分钟，看到运行记录变成绿色 ✓ 即为成功

**确认产出**：回到仓库首页 → **docs/ai-daily/** 目录下应有今天的 `2026-xx-xx.md` 日报文件。

> 以后每天北京时间 05:00 会自动运行，无需手动操作。

---

## 六、第四步：配置 AI 摘要 + 概念解释（三选一）

**统一操作**：仓库 → **Settings** → 左侧 **Secrets and variables** → **Actions** → 点 **New repository secret**，逐个添加（名称必须全大写，值填 Key 本身，**不要写** `${{ }}` 这类语法）。

### 方案 A：不配置（零成本，推荐先跑起来）
什么都不做。日报照常生成，概念解释用内置词表。

### 方案 B：智谱 BigModel 免费档（零成本 + AI 效果）
1. 打开 [open.bigmodel.cn](https://open.bigmodel.cn) 注册登录（手机号即可）
2. 左侧 **API Keys** → **创建 API Key**，复制（只显示一次）
3. 添加 3 个 Secret：
   | Secret 名 | 值 |
   | --- | --- |
   | `LLM_API_KEY` | 刚复制的 Key（`xxxxxxxx.api-key` 格式） |
   | `LLM_BASE_URL` | `https://open.bigmodel.cn/api/paas/v4` |
   | `LLM_MODEL` | `glm-4-flash` |

> glm-4-flash 长期有免费档（以官方页面说明为准），每天一次日报用量很小。

### 方案 C：DeepSeek（很便宜，效果更好）
1. [platform.deepseek.com](https://platform.deepseek.com) 注册 → 充值 10 元即可
2. **API Keys** → 创建 key
3. 3 个 Secret：`LLM_API_KEY`=你的key，`LLM_BASE_URL`=`https://api.deepseek.com/v1`，`LLM_MODEL`=`deepseek-chat`

### 方案 D：OpenAI（需绑卡）
同上，`LLM_BASE_URL`=`https://api.openai.com/v1`，`LLM_MODEL`=`gpt-4o-mini`。

**验证 Key 是否有效**（可选，本地 PowerShell）：
```bash
curl https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer 你的key" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"你好"}]}'
```
返回 JSON 即有效。

---

## 七、第五步：每天邮件推送日报

### 1. 获取邮箱 SMTP 授权码（以 QQ 邮箱为例）
1. 电脑登录 [mail.qq.com](https://mail.qq.com)
2. **设置** → **账户** → 往下找到 **POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV 服务**
3. 把 **SMTP 服务** 一栏点「开启」，按提示用手机发短信验证
4. 成功后页面会显示一串 **16 位授权码**（`abcdefghijklmnop` 格式），**复制保存**（这就是 SMTP 密码）

其他邮箱参考：
| 邮箱 | SMTP 服务器 | 端口 | 授权码获取 |
| --- | --- | --- | --- |
| QQ 邮箱 | `smtp.qq.com` | `465` | 设置→账户→开启 SMTP→短信验证 |
| 163 邮箱 | `smtp.163.com` | `465` | 设置→POP3/SMTP→开启→扫码验证 |
| Gmail | `smtp.gmail.com` | `465` | 账号→安全性→两步验证→应用专用密码 |
| Outlook | `smtp.office365.com` | `587` | 安全设置→启用两步验证→应用密码 |

> 注意：`SMTP_PASSWORD` 填的是**授权码**，不是登录密码！

### 2. 配置 6 个 Secrets（位置同上）
| Secret 名 | 值 |
| --- | --- |
| `SMTP_SERVER` | `smtp.qq.com` |
| `SMTP_PORT` | `465` |
| `SMTP_USERNAME` | 完整邮箱地址 |
| `SMTP_PASSWORD` | 16 位授权码 |
| `MAIL_TO` | 收件邮箱（可填自己） |
| `MAIL_FROM` | 发件人，格式 `AI日报 <你的邮箱@qq.com>` |

### 3. 测试
**Actions → Run workflow** 再跑一次，看日志里 `发送日报邮件` 步骤是否绿色 ✓，然后去邮箱查收（**记得看垃圾箱**）。

---

## 八、第六步：日报同步到你的 GitHub 主页（username.github.io）

### 1. 确认/创建主页仓库
- 若还没有：新建仓库，名字必须**完全等于你的用户名** + `.github.io`，例如 `zhangsan.github.io`，选 Public
- 放一个 `index.html` 作为主页内容（可以先随便放一句 `<h1>我的主页</h1>`）
- 提交后访问 `https://zhangsan.github.io` 应能打开

### 2. 创建 PAT（专用令牌，只给主页仓库权限）
1. GitHub 右上角头像 → **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens**
2. **Generate new token**
   - Token name：`ai-daily-sync`
   - **Repository access**：选 **Only select repositories** → 勾选你的 `username.github.io` 仓库
   - **Permissions** → Repository permissions 里把 **Contents** 设为 **Read and write**
   - 其他保持默认 → **Generate token**
3. **立即复制**（`github_pat_xxxx` 开头，只显示一次）

### 3. 配置 2 个 Secrets
| Secret 名 | 值 |
| --- | --- |
| `HOME_REPO` | `你的用户名/你的用户名.github.io` |
| `HOME_TOKEN` | `github_pat_xxxx` |

### 4. 测试并查看
Run workflow 一次，日志里 `同步日报到 GitHub 主页` 步骤应绿色 ✓。
然后打开 `https://github.com/你的用户名/你的用户名.github.io/ai-daily/`，应能看到今天的 `2026-xx-xx.md`。

> 小提示：GitHub 网页上 .md 文件会直接渲染成排版好的页面，`https://你的用户名.github.io/ai-daily/2026-xx-xx.md` 也能看到。

---

## 九、第七步：调整时间与频率

编辑仓库内 `.github/workflows/ai-daily.yml` 第 6 行的 `cron`（**GitHub 用 UTC 时间 = 北京时间 - 8 小时**）：

| 想在北京时间 | cron 写法 |
| --- | --- |
| 05:00（默认） | `0 21 * * *` |
| 07:00 | `0 23 * * *` |
| 08:30 | `30 0 * * *` |
| 每天 2 次（07:00 / 19:00） | `0 23,11 * * *` |

改完 commit 推上去即可，下次自动运行生效。

---

## 十、日常使用：怎么查看日报

1. **仓库里看**：docs/ai-daily/ 目录，文件名即日期
2. **邮件看**：每天 05:00 后查收
3. **主页看**：`https://你的用户名.github.io/ai-daily/`
4. **做成网页版首页**（可选）：在 ai-daily-news 仓库 Settings → Pages → Source 选 **Deploy from a branch** → main → **/docs** → Save，之后 `https://你的用户名.github.io/ai-daily-news/` 打开即日报索引

---

## 十一、排查手册

| 症状 | 原因 | 解决 |
| --- | --- | --- |
| Actions 里看不到 `AI 每日日报` | 工作流不在**默认分支**上 | 确认推到了 main/master；工作流文件路径必须是 `.github/workflows/ai-daily.yml` |
| Run workflow 点了没反应/找不到按钮 | 工作流文件有语法错误 | 点 Actions 页面的红色叉叉看日志；确认 YAML 缩进 |
| 定时不自动跑 | 仓库 60 天无活动会被暂停 | 手动 Run 一次即恢复；或改一下任何文件推送 |
| 邮件步骤红叉 | 授权码错误 / 端口不对 / 服务未开启 | 重新看第七节；QQ 用 465 端口；SMTP_PASSWORD 必须是授权码 |
| 邮件没收到 | 被丢进垃圾邮件 | 查垃圾箱并标记「不是垃圾邮件」；检查 MAIL_TO 拼写 |
| 日报里没有 AI 摘要 | LLM 调用失败或未配置 | 看日志是否有 `LLM 调用失败(...)`；检查 3 个 Secret 拼写与 Key 余额 |
| LLM 报 401 | Key 错误或已失效 | 重新生成；确认 LLM_BASE_URL 结尾是 `/v1` |
| LLM 报 429 | 额度用尽/限流 | 等一会再跑；或换免费档模型/换服务商 |
| 主页没有更新 | PAT 权限不足 / HOME_REPO 格式错 | 确认 PAT 勾选了主页仓库的 Contents Read and write；HOME_REPO 写 `用户名/用户名.github.io` 没有 `github.com` |
| 日报中文乱码 | 本地用记事本打开 .md 且编码不对 | 文件本身是 UTF-8；用 VS Code / Typora 打开；或直接在 GitHub 网页看 |
| 某个新闻源一直抓不到 | 该 RSS 失效 | 脚本会自动跳过坏源；可编辑脚本顶部 `RSS_FEEDS` 换源 |
| 日报只有 3~4 条新闻 | 48 小时内相关新闻少 | 正常现象；想更多可把 `NEWS_TOP_N` 调大或找新闻源多的时段 |

---

## 十二、全部 Secrets 速查表

| Secret 名 | 必填？ | 用途 | 示例 |
| --- | --- | --- | --- |
| `LLM_API_KEY` | 否 | AI 摘要/概念解释 | `sk-xxxx` |
| `LLM_BASE_URL` | 否 | API 地址 | `https://api.deepseek.com/v1` |
| `LLM_MODEL` | 否 | 模型名 | `deepseek-chat` |
| `SMTP_SERVER` | 否（配邮件必填） | 邮箱 SMTP 服务器 | `smtp.qq.com` |
| `SMTP_PORT` | 否 | SMTP 端口 | `465` |
| `SMTP_USERNAME` | 否 | 邮箱账号 | `xxx@qq.com` |
| `SMTP_PASSWORD` | 否 | 邮箱授权码 | 16 位授权码 |
| `MAIL_TO` | 否 | 收件邮箱 | `xxx@qq.com` |
| `MAIL_FROM` | 否 | 发件人显示 | `AI日报 <xxx@qq.com>` |
| `HOME_REPO` | 否（配主页必填） | 主页仓库 | `用户名/用户名.github.io` |
| `HOME_TOKEN` | 否 | 主页仓库 PAT | `github_pat_xxxx` |

> 添加位置入口：仓库 → Settings → Secrets and variables → Actions → New repository secret

---

## 十三、进阶定制

- **换新闻源**：编辑 `scripts/daily_ai_news.py` 顶部 `RSS_FEEDS` 字典，加一行 `"源名": "RSS地址"` 即可
- **条数**：工作流里 `NEWS_TOP_N: '10'` 改成想要的数量
- **概念解释更准**：配置智谱/DeepSeek 后，LLM 会从当天新闻自动提炼概念，比内置词表好得多
- **加 Telegram/Discord 推送**：在工作流里邮件步骤后面加一个对应 Action 步骤
- **自动转 HTML 网页日报**：可在主页仓库加个 Actions，把 .md 渲染成 .html（或用 GitHub Pages 自动渲染）

## 十四、同类型参考项目

- [notbrighton/ai-daily-digest](https://github.com/notbrighton/ai-daily-digest)：RSS + Markdown 存档 + GitHub Pages
- [Yifannnnnnnnw/ai-dispatch](https://github.com/Yifannnnnnnnw/ai-dispatch)：中文每日 AI 邮件日报
- [danielwipert/ai-news-digest](https://github.com/danielwipert/ai-news-digest)：BART 模型自动摘要
- [Alan-Tomaz/Automatic-News-Feed-Generator](https://github.com/Alan-Tomaz/Automatic-News-Feed-Generator)：邮件 + Telegram 双推送
- [deep-diver/hf-daily-paper-newsletter](https://github.com/deep-diver/hf-daily-paper-newsletter)：HuggingFace 每日论文推送

---

*遇到教程里没覆盖的问题，把 Actions 日志里红叉那一段发给我，我来帮你定位。*
