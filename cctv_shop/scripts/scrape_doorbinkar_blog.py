#!/usr/bin/env python
"""
scripts/scrape_doorbinkar_blog.py
─────────────────────────────────
استخراج مقالات بلاگ سایت قدیمی doorbinkar.com.

خروجی: scripts/output/doorbinkar_blog.json + تصاویر شاخص در
media/education/articles/migrated/

اجرا:
    venv/bin/python scripts/scrape_doorbinkar_blog.py
"""

import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://doorbinkar.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/120"}
DELAY = 1.0

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "scripts" / "output"
IMG_DIR = BASE_DIR / "media" / "education" / "articles" / "migrated"


def get_article_links(session):
    """لینک مقالات از صفحه بلاگ."""
    resp = session.get(f"{BASE}/blog", headers=HEADERS, timeout=30)
    resp.raise_for_status()
    links = {}
    for m in re.finditer(r'href="https://doorbinkar\.com/blog/(\d+)/([^"?]+)"', resp.text):
        links[m.group(1)] = m.group(2)
    return links


def fetch_article(session, legacy_id, slug):
    url = f"{BASE}/blog/{legacy_id}/{slug}"
    resp = session.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    h1 = soup.select_one(".blog-header") or soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""

    def meta(name):
        tag = soup.find("meta", attrs={"name": name})
        return (tag.get("content") or "").strip() if tag else ""

    # تاریخ شمسی مثل 1404/10/15 10:02:09
    date_fa = ""
    container = soup.select_one("#blog-detail")
    if container:
        tm = container.select_one("p.text-muted")
        date_fa = tm.get_text(strip=True) if tm else ""

    author = ""
    if container:
        ap = container.select_one("p.font-weight-bold span")
        author = ap.get_text(strip=True) if ap else ""

    # محتوا — h1 تکراری اول حذف می‌شود
    body = soup.select_one(".post-body")
    content = ""
    if body:
        first_h1 = body.find("h1")
        if first_h1:
            first_h1.decompose()
        content = body.decode_contents().strip()

    # تصویر شاخص — بزرگ‌ترین سایز
    thumb_url = ""
    if container:
        src = container.select_one(".blog-image img")
        if src and src.get("src"):
            thumb_url = src["src"]
    if not thumb_url:
        m = re.search(r"/blog-image/" + re.escape(legacy_id) + r"/[^\"'\s]+-920x518\.webp", resp.text)
        if m:
            thumb_url = BASE + m.group(0)

    keywords = meta("keywords")
    tags = [t.strip() for t in keywords.replace("،", ",").split(",") if t.strip()]
    return {
        "legacy_id": int(legacy_id),
        "legacy_slug": slug,
        "title": title,
        "slug": slug,
        "description": meta("description"),
        "tags": tags,
        "author": author,
        "date_fa": date_fa,
        "content": content,
        "thumbnail_url": thumb_url,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()

    links = get_article_links(session)
    print(f"{len(links)} مقاله پیدا شد")

    articles = []
    for n, (aid, slug) in enumerate(sorted(links.items(), key=lambda x: int(x[0])), 1):
        try:
            a = fetch_article(session, aid, slug)
            # دانلود تصویر شاخص
            a["thumbnail"] = ""
            if a["thumbnail_url"]:
                dest = IMG_DIR / f"{aid}.webp"
                if not dest.exists():
                    r = session.get(a["thumbnail_url"], headers=HEADERS, timeout=60)
                    r.raise_for_status()
                    dest.write_bytes(r.content)
                a["thumbnail"] = f"education/articles/migrated/{aid}.webp"
            articles.append(a)
            print(f"[{n}/{len(links)}] {aid} {a['title'][:50]} | {a['date_fa']} | thumb={'✓' if a['thumbnail'] else '✗'}")
        except Exception as e:
            print(f"[{n}] ! خطا در مقاله {aid}: {e}")
        time.sleep(DELAY)

    out = OUT_DIR / "doorbinkar_blog.json"
    out.write_text(json.dumps(articles, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ ذخیره شد: {out} ({len(articles)} مقاله)")


if __name__ == "__main__":
    main()
