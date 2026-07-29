import hashlib
import time
from datetime import datetime, timezone

import feedparser

FEEDS = [
    {"id": "techcrunch", "url": "https://techcrunch.com/feed/", "tier": "lagging", "region": "global"},
    {"id": "techcrunch_ai", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "tier": "lagging", "region": "global"},
    {"id": "venturebeat", "url": "https://feeds.feedburner.com/venturebeat/SZYF", "tier": "lagging", "region": "global"},
    {"id": "yourstory", "url": "https://yourstory.com/feed", "tier": "lagging", "region": "india"},
    {"id": "producthunt", "url": "https://www.producthunt.com/feed", "tier": "leading", "region": "global"},
    {"id": "hackernews", "url": "https://news.ycombinator.com/rss", "tier": "leading", "region": "global"},
]

USER_AGENT = "stargazer-radar/0.1 (market map prototype)"


def _clean(text):
    if not text:
        return ""
    out = []
    depth = 0
    for ch in text:
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return " ".join("".join(out).split())


def _published(entry):
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return datetime.fromtimestamp(time.mktime(value), tz=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def fetch_feed(feed):
    parsed = feedparser.parse(feed["url"], agent=USER_AGENT)
    records = []
    for entry in parsed.entries:
        title = _clean(entry.get("title", ""))
        summary = _clean(entry.get("summary", ""))[:800]
        url = entry.get("link", "")
        if not title or not url:
            continue
        records.append(
            {
                "id": hashlib.sha1(url.encode()).hexdigest()[:12],
                "title": title,
                "summary": summary,
                "url": url,
                "source_id": feed["id"],
                "tier": feed["tier"],
                "region": feed["region"],
                "published_at": _published(entry),
                "collected_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    return records


def fetch_all(feeds=None):
    feeds = feeds or FEEDS
    seen = set()
    records = []
    errors = []
    for feed in feeds:
        try:
            for record in fetch_feed(feed):
                if record["id"] in seen:
                    continue
                seen.add(record["id"])
                records.append(record)
        except Exception as exc:
            errors.append({"source_id": feed["id"], "error": str(exc)})
    return records, errors
