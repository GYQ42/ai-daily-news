#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 每日日报生成器
================
工作流:
  1. 抓取 RSS / arXiv / Hacker News 中的 AI 相关新闻
  2. 去重、按时间排序, 取最新 TOP_N 条
  3. 配置了 LLM_API_KEY 时调用 OpenAI 兼容接口生成新闻摘要 + 概念解释
     否则用内置词表解释新闻中的常见概念（摘要取原文简介）
  4. 生成 Markdown 日报: docs/ai-daily/<日期>.md
  5. 更新 docs/README.md 存档索引

用法:
  python scripts/daily_ai_news.py             # 正常执行
  python scripts/daily_ai_news.py --selftest  # 不联网, 用示例数据打印预览
"""

import argparse
import datetime
import html
import json
import os
import re
import sys
import time
from urllib.parse import urlencode

import feedparser
import requests

# Windows GBK 控制台也能正常打印 emoji（GitHub Actions 上为 UTF-8，不受影响）
if sys.stdout is not None and sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "docs", "ai-daily")
CST = datetime.timezone(datetime.timedelta(hours=8))
EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AI-Daily-Reporter/1.0)"}

TOP_N = int(os.environ.get("NEWS_TOP_N", "10"))  # 日报收录条数
LOOKBACK_HOURS = 48                              # 优先保留最近 48 小时的新鲜新闻
TODAY = datetime.datetime.now(CST).strftime("%Y-%m-%d")

# ---------------- 新闻源 ----------------
# 键为中文源名，值为 RSS/Atom 地址。某个源失效会被自动跳过，不影响整体。
RSS_FEEDS = {
    "机器之心": "https://www.jiqizhixin.com/rss",
    "InfoQ 中文": "https://www.infoq.cn/feed",
    "OpenAI": "https://openai.com/news/rss.xml",
    "Google AI": "https://blog.google/technology/ai/rss/",
    "MIT News": "https://news.mit.edu/rss/topic/artificial-intelligence2",
    "The Verge": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "VentureBeat": "https://venturebeat.com/category/ai/feed/",
}
ARXIV_QUERY = "cat:cs.AI OR cat:cs.LG OR cat:cs.CL"
ARXIV_ROWS = 8
HN_QUERY = "AI"
HN_ROWS = 20


# ---------------- 工具函数 ----------------

def clean_text(s):
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def truncate(s, n):
    s = clean_text(s)
    if len(s) <= n:
        return s
    return s[:n].rstrip() + "…"


def normalize_key(title):
    t = clean_text(title).lower()
    return re.sub(r"[\W_]+", "", t)


def _dt_ts(dt):
    try:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.timestamp()
    except Exception:
        return None


def fmt_time(dt):
    if not dt:
        return "时间未知"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(CST).strftime("%m-%d %H:%M")


# ---------------- 新闻抓取 ----------------

def fetch_rss_feed(name, url, limit=4):
    out = []
    try:
        feed = feedparser.parse(url, request_headers=HEADERS)
        for e in feed.entries[:limit]:
            published = e.get("published_parsed") or e.get("updated_parsed")
            dt = None
            if published:
                dt = datetime.datetime(*published[:6], tzinfo=datetime.timezone.utc)
            out.append({
                "title": clean_text(e.get("title", "")),
                "link": e.get("link", ""),
                "published": dt,
                "summary": clean_text(e.get("summary", "")),
                "source": name,
            })
    except Exception as exc:
        print("  [!] %s 抓取失败: %s" % (name, exc))
    return out


def fetch_arxiv(rows=8):
    url = "http://export.arxiv.org/api/query?" + urlencode({
        "search_query": ARXIV_QUERY,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": rows,
    })
    out = []
    try:
        feed = feedparser.parse(url)
        for e in feed.entries:
            dt = None
            if e.get("published_parsed"):
                dt = datetime.datetime(*e.published_parsed[:6], tzinfo=datetime.timezone.utc)
            out.append({
                "title": clean_text(e.get("title", "")),
                "link": e.get("link", ""),
                "published": dt,
                "summary": clean_text(e.get("summary", "")),
                "source": "arXiv (cs.AI/LG/CL)",
            })
    except Exception as exc:
        print("  [!] arXiv 抓取失败:", exc)
    return out


def fetch_hackernews(days=2, rows=20):
    since = int(time.time()) - days * 86400
    params = {
        "query": HN_QUERY,
        "tags": "story",
        "numericFilters": "created_at_i>" + str(since),
        "hitsPerPage": rows,
    }
    url = "https://hn.algolia.com/api/v1/search_by_date?" + urlencode(params)
    out = []
    try:
        data = requests.get(url, headers=HEADERS, timeout=20).json()
        for hit in data.get("hits", []):
            title = clean_text(hit.get("title") or "")
            if not re.search(
                r"\b(ai|artificial|machine|llm|gpt|deepseek|openai|anthropic|gemini|model|agent|neural)\b",
                title.lower(),
            ):
                continue
            ts = hit.get("created_at_i")
            dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc) if ts else None
            out.append({
                "title": title,
                "link": hit.get("url") or "https://news.ycombinator.com/item?id=" + str(hit.get("objectID", "")),
                "published": dt,
                "summary": "",
                "source": "Hacker News",
            })
    except Exception as exc:
        print("  [!] Hacker News 抓取失败:", exc)
    return out


def rank_items(items):
    """去重并排序：优先新鲜新闻，不足时用旧新闻补齐。"""
    now = time.time()
    seen = set()
    fresh, stale = [], []
    keyed = sorted(items, key=lambda x: x.get("published") or EPOCH, reverse=True)
    for it in keyed:
        key = normalize_key(it.get("title", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        ts = _dt_ts(it.get("published"))
        if ts is not None and now - ts > LOOKBACK_HOURS * 3600:
            stale.append(it)
        else:
            fresh.append(it)
    return (fresh + stale)[:TOP_N]


def collect_all():
    items = []
    for name, url in RSS_FEEDS.items():
        items += fetch_rss_feed(name, url, limit=4)
    items += fetch_arxiv(ARXIV_ROWS)
    items += fetch_hackernews(2, HN_ROWS)
    return rank_items(items)


# ---------------- LLM 概念解释 ----------------

def llm_explain(items):
    """调用 OpenAI 兼容接口生成摘要与概念解释；失败返回 None 走回退（内置词表）。
    注意: GitHub Models 已于 2026-07-30 退役，这里只支持自己的 OpenAI 兼容 Key。"""
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    base = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    if not api_key:
        return None

    news_block = "\n".join(
        '%d. 《%s》 来源:%s 链接:%s 简介:%s'
        % (i + 1, it["title"], it["source"], it["link"], truncate(it["summary"], 200))
        for i, it in enumerate(items)
    )
    prompt = (
        "你是一个 AI 新闻编辑。今天是 %s。以下是今天收集的 %d 条 AI 新闻：\n----\n%s\n----\n"
        "请只输出如下格式的 JSON（不要输出其他任何内容）：\n"
        '{"items":[{"index":1,"summary":"不超过60字的中文摘要"},...],'
        '"concepts":[{"term":"概念名","explanation":"2-3句通俗中文解释"}]}\n'
        "要求：1) items 与新闻一一对应，index 从 1 开始；"
        "2) concepts 从这些新闻中提炼 3~6 个值得解释的概念/术语/公司/模型；"
        "3) 解释面向普通读者，通俗易懂。"
    ) % (TODAY, len(items), news_block)
    try:
        resp = requests.post(
            base + "/chat/completions",
            headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            },
            timeout=120,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return parse_llm_json(content, len(items))
    except Exception as exc:
        print("  [!] LLM 调用失败(%s)，使用内置词表回退" % exc)
        return None


def parse_llm_json(content, n):
    info = {"summaries": {}, "concepts": []}
    text = content.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        text = m.group(0)
    try:
        data = json.loads(text)
    except Exception:
        return info
    for it in data.get("items", []) or []:
        idx = it.get("index")
        s = it.get("summary") or ""
        if isinstance(idx, int) and s:
            info["summaries"][idx] = truncate(s, 120)
    for c in data.get("concepts", []) or []:
        term = (c.get("term") or "").strip()
        exp = (c.get("explanation") or "").strip()
        if term and exp:
            info["concepts"].append({"term": truncate(term, 40), "explanation": exp})
    return info


# ---------------- 内置词表回退 ----------------
# key: 匹配关键词 -> (展示名, 通俗解释)。无 LLM Key 时用它对新闻标题做关键词匹配。

GLOSSARY = {
    "llm": ("LLM / 大语言模型", "基于海量文本训练、能理解和生成自然语言的大型神经网络模型，如 GPT、DeepSeek、Claude。"),
    "rag": ("RAG / 检索增强生成", "让模型先检索外部资料库，再基于检索结果作答，减少幻觉并可以引用来源。"),
    "agent": ("Agent / AI 智能体", "能自主规划、调用工具并执行多步任务来达成目标的 AI 程序。"),
    "multimodal": ("多模态", "模型能同时处理文本、图像、音频甚至视频，如 GPT-4o、Gemini。"),
    "fine-tuning": ("微调 (Fine-tuning)", "在预训练模型基础上用特定数据继续训练，让模型更擅长某个领域或风格。"),
    "prompt": ("提示词工程 (Prompt)", "通过精心设计输入指令来引导模型输出的技巧。"),
    "token": ("Token", "模型处理文本的基本单位，大致相当于一个词的一部分；计费与上下文长度都以 token 计算。"),
    "transformer": ("Transformer", "2017 年提出的深度学习架构，靠注意力机制并行处理序列，是大模型的基础。"),
    "diffusion": ("扩散模型", "通过逐步去噪生成图像/视频的模型，Stable Diffusion、Sora 等基于该思想。"),
    "agi": ("AGI / 通用人工智能", "能在绝大多数任务上达到或超越人类水平的人工智能，是业界长期目标。"),
    "alignment": ("AI 对齐", "让 AI 的行为符合人类意图与价值观的技术方向，如 RLHF。"),
    "hallucination": ("幻觉", "模型一本正经地编造看似合理但错误的内容，是大模型的主要缺陷之一。"),
    "context window": ("上下文窗口", "模型单次能容纳的输入长度，窗口越大一次可处理的信息越多。"),
    "embedding": ("Embedding / 向量化", "把文字、图片等转为高维数值向量，用于语义搜索与相似度比较。"),
    "vector database": ("向量数据库", "专门存储和检索向量的数据库，常与 Embedding 配合实现语义检索（RAG 的核心组件）。"),
    "rlhf": ("RLHF / 人类反馈强化学习", "用人类偏好反馈训练模型，让输出更符合人类期望。"),
    "distillation": ("知识蒸馏", "用大模型输出训练小模型，让小模型以更低成本接近大模型能力。"),
    "moe": ("MoE / 混合专家", "把模型拆成多个专家网络，每次只激活部分专家，用更低算力支撑更大模型。"),
    "reasoning model": ("推理模型", "如 o1、DeepSeek-R1，先“思考”再作答，擅长数学、代码等复杂推理任务。"),
    "mcp": ("MCP / 模型上下文协议", "Anthropic 提出的开放协议，统一 AI 应用与外部工具/数据源的连接方式。"),
    "embodied": ("具身智能", "让 AI 拥有身体（机器人）并与物理世界交互，是 AI 前沿热门方向。"),
    "aigc": ("AIGC / AI 生成内容", "用 AI 生成文本、图像、音频、视频等内容的总称。"),
    "openai": ("OpenAI", "开发 ChatGPT/GPT 系列的 AI 公司，行业风向标。"),
    "deepseek": ("DeepSeek", "中国 AI 公司（深度求索），以开源大模型 DeepSeek-R1/V3 闻名。"),
    "anthropic": ("Anthropic", "开发 Claude 系列的 AI 公司，强调 AI 安全与对齐。"),
    "gemini": ("Gemini", "Google 推出的多模态大模型系列。"),
    "nvidia": ("NVIDIA", "AI 算力龙头，GPU 与 CUDA 生态的提供者。"),
    "meta": ("Meta (FAIR)", "Meta 的 AI 研究部门，开源了 Llama 系列模型。"),
    "copilot": ("GitHub Copilot", "GitHub 的 AI 编程助手，可在编辑器内补全代码、解释代码。"),
}


def glossary_explain(items):
    concepts = []
    seen = set()
    for it in items:
        text = (it["title"] + " " + (it["summary"] or "")).lower()
        for key, (name, desc) in GLOSSARY.items():
            if key in text and key not in seen:
                seen.add(key)
                concepts.append({"term": name, "explanation": desc})
        if len(concepts) >= 6:
            break
    return concepts


def fallback_summary(it):
    s = clean_text(it.get("summary", ""))
    if s:
        return truncate(s, 120)
    return "（该新闻无摘要，点击链接查看原文）"


# ---------------- 日报渲染 ----------------

def render_report(items, concepts, summaries, used_llm):
    lines = []
    lines.append("# 🤖 AI 每日日报 · " + TODAY)
    lines.append("")
    lines.append("> ⏰ 自动生成 ｜ 📰 " + str(len(items)) + " 条新闻 ｜ 💡 概念解释：" + ("AI 生成" if used_llm else "内置词表（配置 LLM Key 可获得智能解读）"))
    lines.append("> 📡 数据源：RSS 科技媒体 / arXiv / Hacker News")
    lines.append("")
    lines.append("## 📰 今日新闻")
    lines.append("")
    if not items:
        lines.append("> ⚠️ 本次未收集到新闻（可能数据源暂时不可用），请查看 GitHub Actions 日志。")
        lines.append("")
    for i, it in enumerate(items, 1):
        lines.append("### " + str(i) + ". " + it["title"])
        lines.append("")
        lines.append("- 🔗 " + it["link"])
        lines.append("- 📡 来源：" + it["source"] + " ｜ 🕐 " + fmt_time(it.get("published")))
        lines.append("")
        lines.append("💬 " + (summaries.get(i) or fallback_summary(it)))
        lines.append("")
    lines.append("## 🔑 今日概念解释")
    lines.append("")
    if not concepts:
        lines.append("> 未匹配到需要解释的概念。配置 LLM_API_KEY 后可由 AI 自动从新闻中提炼并解释概念。")
        lines.append("")
    for c in concepts:
        lines.append("### " + c["term"])
        lines.append("")
        lines.append(c["explanation"])
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*本日报由 GitHub Actions 自动生成，数据来自公开新闻源，仅供学习参考。*")
    lines.append("")
    return "\n".join(lines)


def write_report(md):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, TODAY + ".md")
    with open(path, "w", encoding="utf-8") as fp:
        fp.write(md)
    return path


def update_index():
    os.makedirs(OUT_DIR, exist_ok=True)
    files = sorted(
        (f for f in os.listdir(OUT_DIR) if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.md", f)),
        reverse=True,
    )
    lines = ["# 📚 AI 日报存档", "", "| 日期 | 日报 |", "| --- | --- |"]
    for f in files[:30]:
        lines.append("| " + f[:-3] + " | [查看日报](./ai-daily/" + f + ") |")
    lines.append("")
    lines.append("> 📌 最新一份生成于 " + datetime.datetime.now(CST).strftime("%Y-%m-%d %H:%M") + "（北京时间）")
    index_path = os.path.join(BASE_DIR, "docs", "README.md")
    with open(index_path, "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines))


# ---------------- 主入口 ----------------

def main():
    parser = argparse.ArgumentParser(description="AI 每日日报生成器")
    parser.add_argument("--selftest", action="store_true", help="不联网，用示例数据打印日报预览")
    args = parser.parse_args()

    if args.selftest:
        now_cst = datetime.datetime.now(CST)
        samples = [
            {"title": "OpenAI 发布新一代推理模型，数学与编程能力大幅提升",
             "link": "https://example.com/news/openai-reasoning",
             "published": now_cst,
             "summary": "OpenAI 推出新一代推理模型，在数学、代码等复杂任务上超越前代，并已向 API 用户开放。",
             "source": "示例（selftest）"},
            {"title": "DeepSeek 开源升级版模型，支持百万级 Token 上下文",
             "link": "https://example.com/news/deepseek",
             "published": now_cst,
             "summary": "DeepSeek 发布新版本开源模型，上下文窗口大幅扩展，推理成本进一步下降。",
             "source": "示例（selftest）"},
            {"title": "NVIDIA 发布新一代 AI 加速芯片，大模型训练成本降低 60%",
             "link": "https://example.com/news/nvidia",
             "published": now_cst,
             "summary": "NVIDIA 在 GTC 大会上发布新一代芯片，并宣布多家云厂商已采用。",
             "source": "示例（selftest）"},
            {"title": "Google DeepMind 提出新 Agent 框架，可自主调用工具完成多步任务",
             "link": "https://example.com/news/agent",
             "published": now_cst,
             "summary": "DeepMind 发布新的智能体框架，支持浏览器操作与代码执行。",
             "source": "示例（selftest）"},
        ]
        md = render_report(samples, glossary_explain(samples), {}, False)
        print(md)
        return

    print("=" * 50)
    print("[%s] 开始收集 AI 新闻…" % TODAY)
    items = collect_all()
    print("  去重排序后得到 %d 条，收录前 %d 条" % (len(items), TOP_N))
    items = items[:TOP_N]

    info = llm_explain(items)
    if info:
        concepts = info["concepts"]
        summaries = info["summaries"]
        used_llm = True
    else:
        concepts = glossary_explain(items)
        summaries = {}
        used_llm = False

    md = render_report(items, concepts, summaries, used_llm)
    path = write_report(md)
    update_index()
    print("  ✔ 日报已生成: %s" % path)
    print("  ✔ docs/README.md 索引已更新")
    print("=" * 50)


if __name__ == "__main__":
    main()
