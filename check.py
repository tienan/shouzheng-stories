"""Check the generated site's links, anchors, titles and XML before publishing."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.links = []
        self.ids = set()
        self.headings = 0
        self.title = False

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if "id" in attrs:
            assert attrs["id"] not in self.ids, f"Duplicate id: {self.path}: {attrs['id']}"
            self.ids.add(attrs["id"])
        if tag == "h1":
            self.headings += 1
        if tag == "title":
            self.title = True
        if tag in ("a", "link") and "href" in attrs:
            self.links.append(attrs["href"])
        if tag in ("img", "script") and "src" in attrs:
            self.links.append(attrs["src"])
        if tag == "img":
            assert attrs.get("alt"), f"Missing image alt: {self.path}"


pages = {}
for path in DOCS.rglob("*.html"):
    page = Page(path)
    page.feed(path.read_text(encoding="utf-8"))
    assert page.headings == 1, f"Expected one H1: {path}"
    assert page.title, f"Missing title: {path}"
    pages[path.resolve()] = page

link_count = 0
for path, page in pages.items():
    for url in page.links:
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc:
            continue
        target = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
        if target.is_dir():
            target = target / "index.html"
        assert target.is_relative_to(DOCS.resolve()), f"Link escapes public site: {path}: {url}"
        assert target.exists(), f"Broken link: {path}: {url}"
        if parsed.fragment and target in pages:
            assert parsed.fragment in pages[target].ids, f"Broken anchor: {path}: {url}"
        link_count += 1

for name in ("sitemap.xml", "feed.xml"):
    ET.parse(DOCS / name)

config = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
assert len(pages) == len(config["book"]["chapters"]) + 3
for path in pages:
    text = path.read_text(encoding="utf-8")
    assert "陈砚" not in text and "毛教员" not in text, f"Previous protagonist in public page: {path}"
    assert "禁言" not in text and "处罚通知" not in text, f"Private publishing history in public page: {path}"

print(json.dumps({"pages": len(pages), "local_links": link_count, "xml": "valid", "public_content": "passed"}, ensure_ascii=False))
