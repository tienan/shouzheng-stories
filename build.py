"""Build the public reading site with Python's standard library only."""
from __future__ import annotations

import argparse
import html
import json
import math
import os
from pathlib import Path
import re
import shutil
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
OUT = ROOT / "docs"
BOOK = CONFIG["book"]
SITE_URL = CONFIG["url"].rstrip("/")


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def link(route: str, current: str) -> str:
    target = f"{route.strip('/')}/index.html" if route.strip("/") else "index.html"
    result = os.path.relpath(target, os.path.dirname(current) or ".").replace("\\", "/")
    if result.endswith("index.html"):
        result = result[:-10]
    return result or "./"


def asset(path: str, current: str) -> str:
    return os.path.relpath(path, os.path.dirname(current) or ".").replace("\\", "/")


def inline(text: str) -> str:
    value = esc(text)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)

    def replace_link(match: re.Match) -> str:
        url = html.unescape(match[2])
        if urlsplit(url).scheme not in ("", "http", "https", "mailto"):
            return match[1]
        return f'<a href="{esc(url)}">{match[1]}</a>'

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace_link, value)


def body_from_markdown(path: Path) -> str:
    lines = path.read_text(encoding="utf-8-sig").strip().splitlines()
    if lines and lines[0].startswith("# "):
        lines.pop(0)
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and lines[0].startswith(">") and "历史穿越小说" in lines[0]:
        lines.pop(0)
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and lines[0].startswith("## "):
        lines.pop(0)
    return "\n".join(lines).strip()


def markdown(text: str) -> str:
    blocks = re.split(r"\n\s*\n", text)
    output = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if block in ("***", "---", "* * *"):
            output.append('<hr aria-label="场景转换">')
        elif block.startswith(">"):
            content = " ".join(re.sub(r"^>\s?", "", x) for x in block.splitlines())
            output.append(f"<blockquote><p>{inline(content)}</p></blockquote>")
        elif re.match(r"^#{1,6} ", block):
            marker, text = block.split(" ", 1)
            level = min(4, max(2, len(marker)))
            output.append(f"<h{level}>{inline(text)}</h{level}>")
        elif all(re.match(r"^[-*] ", x) for x in block.splitlines()):
            output.append("<ul>" + "".join(f"<li>{inline(x[2:])}</li>" for x in block.splitlines()) + "</ul>")
        else:
            output.append(f"<p>{inline(' '.join(block.splitlines()))}</p>")
    return "\n".join(output)


CHAPTERS = []
for item in BOOK["chapters"]:
    data = dict(item)
    data["route"] = f'{BOOK["slug"]}/{item["id"]}'
    data["body"] = body_from_markdown(ROOT / item["file"])
    data["count"] = len(re.findall(r"[\u4e00-\u9fff]", data["body"]))
    data["minutes"] = max(1, math.ceil(data["count"] / 400))
    CHAPTERS.append(data)


def chapter_rows(current: str) -> str:
    rows = []
    for chapter in CHAPTERS:
        rows.append(f'''<a class="chapter-row" href="{link(chapter['route'], current)}">
          <span class="chapter-number">{esc(chapter['label'])}</span>
          <div class="chapter-summary"><h3>{esc(chapter['title'])}</h3><p>{esc(chapter['description'])}</p></div>
          <span class="chapter-meta">约 {chapter['minutes']} 分钟 <span aria-hidden="true">↗</span></span>
        </a>''')
    return "\n".join(rows)


def page(current: str, title: str, description: str, content: str, kind: str = "home") -> str:
    route = current.removesuffix("index.html").rstrip("/")
    canonical = SITE_URL + ("/" + route if route else "/")
    nav = []
    for target, label, selected in (("", "首页", kind == "home"), ("meiji", "明治未明", kind in ("book", "reader")), ("about", "关于", kind == "about")):
        nav.append(f'<a href="{link(target, current)}"' + (' aria-current="page"' if selected else '') + f'>{label}</a>')
    return f'''<!doctype html>
<html lang="zh-CN" data-theme="light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>{esc(title)} · {esc(CONFIG['name'])}</title>
  <meta name="description" content="{esc(description)}">
  <link rel="canonical" href="{esc(canonical)}">
  <meta property="og:type" content="{'article' if kind == 'reader' else 'website'}">
  <meta property="og:locale" content="zh_CN">
  <meta property="og:title" content="{esc(title)} · {esc(CONFIG['name'])}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:url" content="{esc(canonical)}">
  <meta property="og:image" content="{esc(SITE_URL + '/' + BOOK['cover'])}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" href="{asset('assets/favicon.svg', current)}" type="image/svg+xml">
  <link rel="alternate" type="application/rss+xml" title="守正异闻录 · 连载更新" href="{asset('feed.xml', current)}">
  <script>try{{const p=JSON.parse(localStorage.getItem('sz.preferences')||'{{}}');if(['light','dark','sepia'].includes(p.theme))document.documentElement.dataset.theme=p.theme;if(p.fontSize>=16&&p.fontSize<=28)document.documentElement.style.setProperty('--reader-size',p.fontSize+'px');if([720,860].includes(p.width))document.documentElement.style.setProperty('--reader-width',p.width+'px')}}catch(e){{}}</script>
  <link rel="stylesheet" href="{asset('assets/site.css', current)}">
  <script src="{asset('assets/site.js', current)}" defer></script>
</head>
<body class="page-{kind}" data-site-root="{link('', current)}">
  <a class="skip-link" href="#main">跳至正文</a>
  {'<div class="reading-progress" aria-hidden="true"></div>' if kind == 'reader' else ''}
  <header class="site-header"><div class="header-inner">
    <a class="brand" href="{link('', current)}" aria-label="守正异闻录首页"><span class="brand-mark" aria-hidden="true">正</span><span class="brand-name">守正异闻录<small>SHOUZHENG STORIES</small></span></a>
    <nav class="site-nav" aria-label="主导航">{''.join(nav)}</nav>
    <button class="theme-toggle" type="button" aria-label="切换夜间模式" title="切换夜间模式"><span aria-hidden="true">◐</span><span class="theme-label">夜读</span></button>
  </div></header>
  <main id="main">{content}</main>
  <footer class="site-footer"><div class="footer-inner"><div><span class="footer-brand">守正异闻录</span><p>让故事里的人，拥有自己的声音。</p></div><nav aria-label="页脚导航"><a href="{link('meiji', current)}">连载目录</a><a href="{asset('feed.xml', current)}">RSS 订阅</a><a href="{link('about', current)}">关于本站</a></nav><small>© 2026 守正异闻录</small></div></footer>
</body>
</html>'''


def home() -> str:
    current = "index.html"
    return page(current, "一个普通人的历史异闻", CONFIG["description"], f'''
    <section class="hero container" aria-labelledby="hero-title">
      <div class="hero-copy"><p class="eyebrow">原创小说 / 首部连载</p>
        <h1 class="hero-title" id="hero-title">故事从一盆<br>炭火开始。</h1>
        <p class="hero-deck">他在旧书摊偶然翻到一本红色小手册。再睁眼时，成了明治维新前夜的少年天皇。<br>他想召见一个送炭的孩子，口谕却在回廊里变了样。</p>
        <div class="hero-actions"><a class="button-primary" href="{link(CHAPTERS[0]['route'], current)}">开始阅读 <span aria-hidden="true">→</span></a><a class="button-text" href="{link('meiji', current)}">查看连载目录 <span aria-hidden="true">↗</span></a></div>
        <p class="hero-footnote">《明治未明》<span aria-hidden="true">／</span>历史穿越<span aria-hidden="true">／</span>更新至{esc(CHAPTERS[-1]['title'].split('　')[0])}</p>
        <a id="continue-reading" class="text-link" hidden>继续上次阅读 <span aria-hidden="true">→</span></a>
      </div>
      <figure class="hero-art"><img class="cover-image" src="{asset(BOOK['cover'], current)}" width="1086" height="1448" alt="《明治未明》封面：少年天皇坐在炭火与纸笔旁，望向京都御所的幽深回廊" fetchpriority="high"><figcaption class="cover-caption"><span>明治未明</span><span>MEIJI BEFORE DAWN</span></figcaption></figure>
    </section>
    <section class="container section-rule" id="stories" aria-labelledby="start-heading">
      <div class="section-heading"><p class="eyebrow">从这里读起 / THE SERIAL</p><h2 id="start-heading">明治未明</h2><p>1867 年，京都。一个新的身份，一道尚未走出宫门的命令。</p></div>
      <div class="chapter-list">{chapter_rows(current)}</div>
    </section>
    <section class="container character-section section-rule" aria-labelledby="character-heading">
      <div class="character-quote"><p class="eyebrow">第一节 · 炭火</p><blockquote>“我说让清吉来。<br>这上面没有。”</blockquote><a class="text-link" href="{link('meiji/01', current)}">读这一节 <span aria-hidden="true">→</span></a></div>
      <div class="character-copy"><p class="eyebrow">故事里的人 / SHOUZHENG</p><h2 id="character-heading">守正，仍在学习。</h2><p>三十二岁，制造企业的基层主管。别人答得慢，他容易着急；轮到写停工说明，却改了三遍，还在犹豫要不要写上采购部经理的名字。</p><p>到了京都御所，他还是想尽快把事情办好。可送炭的孩子有自己的难处，也有比回答他的问题更着急的事。</p><a class="text-link" href="{link('about', current)}">关于守正与这个故事 <span aria-hidden="true">↗</span></a></div>
    </section>''')


def book_page() -> str:
    current = "meiji/index.html"
    return page(current, BOOK["title"], "《明治未明》连载目录。普通车间主管守正，穿越成为1867年的少年天皇。", f'''
    <div class="container"><p class="breadcrumb"><a href="{link('', current)}">首页</a><span aria-hidden="true">/</span>当前连载</p>
    <section class="book-header"><div class="book-cover"><img class="cover-image" src="{asset(BOOK['cover'], current)}" width="1086" height="1448" alt="明治未明小说封面"></div><div class="book-copy"><p class="eyebrow">守正异闻录 / 第一部</p><h1 class="book-title">明治未明</h1><div class="book-meta"><span>历史穿越</span><span>1867 · 京都</span><span class="book-status">连载中</span></div><div class="book-description"><p>一个雨天，车间主管守正在旧书摊翻到一本红色小手册，带回住处断断续续地读。一觉醒来，门外的人却称他“陛下”。</p><p>他知道日本后来会走向怎样的战争，却不懂眼前的朝廷、藩政和人情。要改变什么，先得弄清一笔炭钱为什么付不出去。</p></div><div class="hero-actions"><a class="button-primary" href="{link(CHAPTERS[0]['route'], current)}">从引言开始 <span aria-hidden="true">→</span></a><a class="button-text" href="#chapters">查看目录 ↓</a></div></div></section>
    <section class="section-rule" id="chapters" aria-labelledby="contents-heading"><div class="section-heading"><p class="eyebrow">CONTENTS</p><h2 id="contents-heading">连载目录</h2><p>每次一节，约三千字。按顺序读，也可回到熟悉的一页。</p></div><div class="chapter-list">{chapter_rows(current)}</div><p class="reader-endnote">下一节正在酝酿。新章节发布后，将接续更新在这里。</p></section></div>''', "book")


def chapter_page(chapter: dict, position: int) -> str:
    current = chapter["route"] + "/index.html"
    previous = f'<a class="nav-previous" href="{link(CHAPTERS[position-1]["route"], current)}">← {esc(CHAPTERS[position-1]["title"])}</a>' if position else '<span class="nav-previous" aria-disabled="true">故事由此开始</span>'
    following = f'<a class="nav-next" href="{link(CHAPTERS[position+1]["route"], current)}">{esc(CHAPTERS[position+1]["title"])} →</a>' if position + 1 < len(CHAPTERS) else '<span class="nav-next" aria-disabled="true">下一节 · 尚未更新</span>'
    return page(current, f'{BOOK["title"]}｜{chapter["title"]}', chapter["description"], f'''
    <div class="reader-shell"><p class="breadcrumb"><a href="{link('', current)}">首页</a><span aria-hidden="true">/</span><a href="{link('meiji', current)}">明治未明</a><span aria-hidden="true">/</span>{esc(chapter['title'])}</p>
    <header class="reader-heading"><p class="reader-kicker">明治未明 / {esc(chapter['label'])}</p><h1>{esc(chapter['title'])}</h1><p class="reader-meta">约 {chapter['count']:,} 字 <span aria-hidden="true">·</span> 阅读约 {chapter['minutes']} 分钟</p></header>
    <div class="reader-toolbar" role="group" aria-label="阅读设置"><span>阅读设置</span><button type="button" data-font="smaller" aria-label="缩小正文字号">A−</button><button type="button" data-font="larger" aria-label="放大正文字号">A＋</button><button type="button" data-width aria-pressed="false">宽版</button><button type="button" data-paper aria-pressed="false">暖纸</button><span id="reader-feedback" class="sr-only" role="status" aria-live="polite"></span></div>
    <article class="prose" data-reader-title="{esc(chapter['title'])}">{markdown(chapter['body'])}</article>
    <p class="reader-endnote">{('引言完 · 下一页进入故事。' if position == 0 else '本节完 · 《明治未明》持续连载。')}</p><nav class="chapter-navigation" aria-label="章节导航">{previous}<a class="nav-index" href="{link('meiji', current)}#chapters">返回目录</a>{following}</nav>
    <p class="reading-position">阅读设置与进度仅保存在你当前使用的浏览器。</p></div><button type="button" class="back-top" aria-label="回到页面顶部" hidden>↑</button>''', "reader")


def about_page() -> str:
    current = "about/index.html"
    return page(current, "关于守正异闻录", "关于守正、明治未明，以及这个安静的小说阅读站。", f'''
    <div class="container"><p class="breadcrumb"><a href="{link('', current)}">首页</a><span aria-hidden="true">/</span>关于本站</p><header class="section-heading"><p class="eyebrow">ABOUT THE STORIES</p><h1>让每个人，<br>都有自己的来处。</h1></header>
    <div class="about-layout"><article class="about-main prose"><h2>守正是谁</h2><p>守正三十二岁，在制造企业管着一个车间。出了问题，他习惯一口气问到底；轮到给上级的停工说明，却把同一句话改了三遍。一个雨天，他等车时在旧书摊偶然翻到一本小手册，掌心大小，红色封面已经磨白，后来带回住处，睡前断断续续地读。</p><p>有些页让他想起车间里的人：谁真正做过这件事，谁还没被问到，一句“已经办了”究竟算不算办完。他把这些问号带到了京都，也把自己的急脾气和犹豫一起带了过去。一个送炭的孩子，会让他把准备好的问题先放下来。</p><h2>当前连载：《明治未明》</h2><p>故事从1867年的京都御所开始。守正醒来，成了少年天皇睦仁。他对未来的认识只是历史的大轮廓，对眼前的宫廷、藩政与社会仍须重新了解。</p><p>一个送炭的孩子，把他带进了第一件需要处理的事。此后的故事，将从人物对话、具体事件和每次选择的后果中逐步展开。</p><p>本作为架空历史小说，包含原创人物、虚构对话与情节。</p><h2>关于阅读与更新</h2><p>小说按节连载，每节约三千字。新读者可以从引言读起，已读的章节始终保留在目录中。也可以通过 RSS 订阅更新。</p><p>字号、纸色与阅读位置保存在当前浏览器中。更换浏览器或清除本机数据后，这些偏好不会同步保留。</p><h2>关于创作</h2><p>小说与视觉素材的制作使用了人工智能工具。故事设定、人物选择及修订随连载持续发展。</p></article><aside class="about-aside"><p class="eyebrow">正在连载</p><h2>明治未明</h2><p>一道召见的口谕，<br>在回廊里变了样。</p><a class="button-primary" href="{link('meiji', current)}">进入故事 →</a></aside></div></div>''', "about")


def build() -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / "assets").mkdir(exist_ok=True)
    for source in (ROOT / "assets").iterdir():
        if source.is_file():
            shutil.copy2(source, OUT / "assets" / source.name)
    pages = {"index.html": home(), "meiji/index.html": book_page(), "about/index.html": about_page()}
    for index, chapter in enumerate(CHAPTERS):
        pages[chapter["route"] + "/index.html"] = chapter_page(chapter, index)
    for path, content in pages.items():
        destination = OUT / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8", newline="\n")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")
    sitemap = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for path in pages:
        item = ET.SubElement(sitemap, "url")
        route = path.removesuffix("index.html")
        ET.SubElement(item, "loc").text = SITE_URL + "/" + route
        ET.SubElement(item, "lastmod").text = CONFIG["updated"]
    ET.ElementTree(sitemap).write(OUT / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    for key, value in (("title", CONFIG["name"]), ("link", SITE_URL), ("description", CONFIG["description"]), ("language", "zh-CN")):
        ET.SubElement(channel, key).text = value
    for chapter in reversed(CHAPTERS):
        item = ET.SubElement(channel, "item")
        url = SITE_URL + "/" + chapter["route"] + "/"
        for key, value in (("title", BOOK["title"] + "｜" + chapter["title"]), ("link", url), ("guid", url), ("description", chapter["description"])):
            ET.SubElement(item, key).text = value
    ET.ElementTree(rss).write(OUT / "feed.xml", encoding="utf-8", xml_declaration=True)
    print(json.dumps({"pages": len(pages), "chapters": len(CHAPTERS), "output": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    build()
