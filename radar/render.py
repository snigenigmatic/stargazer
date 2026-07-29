import html
import json
from datetime import datetime, timezone

from .taxonomy import CATEGORIES
from .digest import _age_days, meeting_score, needs_review

CSS = """
:root{
  --ink:#14161A; --paper:#EEEFEA; --rule:#C9CBC3; --dim:#8B8F86;
  --signal:#1F3BE0; --flag:#A8412B; --card:#F7F7F4;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:"IBM Plex Sans",system-ui,sans-serif;font-size:15px;line-height:1.5}
.wrap{max-width:1180px;margin:0 auto;padding:40px 24px 96px}
header{border-bottom:2px solid var(--ink);padding-bottom:20px;margin-bottom:8px}
h1{font-family:"Fraunces",Georgia,serif;font-weight:600;font-size:clamp(30px,5vw,52px);
  line-height:1.02;margin:0 0 10px;letter-spacing:-.02em}
.sub{font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--dim);
  text-transform:uppercase;letter-spacing:.08em}
.asof{display:flex;flex-wrap:wrap;gap:20px;margin-top:14px;
  font-family:"IBM Plex Mono",monospace;font-size:12px}
.asof b{font-weight:600;color:var(--ink)}
.legend{display:flex;flex-wrap:wrap;gap:18px;padding:14px 0;border-bottom:1px solid var(--rule);
  font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--dim);
  text-transform:uppercase;letter-spacing:.06em}
.band{border-bottom:1px solid var(--rule);padding:30px 0}
.bandhead{display:flex;flex-wrap:wrap;align-items:baseline;gap:14px;margin-bottom:4px}
.bandhead h2{font-family:"Fraunces",Georgia,serif;font-size:24px;font-weight:600;margin:0;
  letter-spacing:-.01em}
.buys{font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--dim)}
.thesis{font-size:13.5px;color:#4A4E48;max-width:62ch;margin:0 0 18px}
.delta{font-family:"IBM Plex Mono",monospace;font-size:11px;padding:2px 7px;border:1px solid var(--rule)}
.delta.up{color:var(--signal);border-color:var(--signal)}
.delta.down{color:var(--flag);border-color:var(--flag)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(248px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--rule);padding:0 14px 12px 4px;
  display:grid;grid-template-columns:20px 1fr}
.gutter{display:flex;flex-direction:column;gap:3px;padding:15px 0 12px 6px}
.tick{width:7px;height:2px;background:var(--ink);opacity:.55}
.name{font-weight:600;font-size:16px;margin:12px 0 2px;letter-spacing:-.01em}
.meta{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--dim);
  display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px}
.meta .new{color:var(--signal)}
.headline{font-size:13px;color:#4A4E48;margin:0 0 8px}
.headline a{color:inherit;text-decoration:none;border-bottom:1px solid var(--rule)}
.headline a:hover,.headline a:focus{border-color:var(--signal);color:var(--signal)}
.prov{font-family:"IBM Plex Mono",monospace;font-size:10px;color:var(--dim);
  text-transform:uppercase;letter-spacing:.06em}
.decay-1{opacity:.82}.decay-2{opacity:.62}.decay-3{opacity:.44}
.empty{font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--dim)}
footer{margin-top:44px;padding-top:18px;border-top:2px solid var(--ink);
  font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--dim);max-width:70ch}
a:focus-visible{outline:2px solid var(--signal);outline-offset:2px}
@media (prefers-reduced-motion:no-preference){.card{transition:border-color .15s}}
.card:hover{border-color:var(--ink)}
@media (max-width:620px){.wrap{padding:24px 16px 64px}.grid{grid-template-columns:1fr}}
"""


def _decay_class(days):
    if days <= 2:
        return ""
    if days <= 6:
        return "decay-1"
    if days <= 13:
        return "decay-2"
    return "decay-3"


def render(store, digest, path):
    entities = store.data["entities"]
    momentum = {row["category"]: row for row in digest["momentum"]}
    buckets = {key: [] for key in CATEGORIES}
    buckets["unclassified"] = []

    buckets["review"] = []
    for key, entity in entities.items():
        category = (entity.get("facts", {}).get("category") or {}).get("value")
        if needs_review(entity):
            buckets["review"].append((key, entity))
            continue
        buckets.setdefault(category or "unclassified", []).append((key, entity))

    parts = [
        "<!doctype html><html lang=en><head><meta charset=utf-8>",
        '<meta name=viewport content="width=device-width,initial-scale=1">',
        "<title>Consumer AI radar</title>",
        '<link rel=preconnect href="https://fonts.googleapis.com">',
        '<link rel=preconnect href="https://fonts.gstatic.com" crossorigin>',
        '<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&'
        'family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;600&display=swap" rel=stylesheet>',
        f"<style>{CSS}</style></head><body><div class=wrap>",
        "<header>",
        "<div class=sub>Stargazer &middot; consumer AI</div>",
        "<h1>The map is a view,<br>not a document.</h1>",
        '<div class=asof>',
        f'<span>as of <b>{digest["generated_at"][:16].replace("T", " ")} UTC</b></span>',
        f'<span>companies <b>{digest["counts"]["entities"]}</b></span>',
        f'<span>changes this run <b>{digest["counts"]["changes"]}</b></span>',
        f'<span>new this run <b>{digest["counts"]["new"]}</b></span>',
        "</div></header>",
        "<div class=legend>",
        "<span>one tick = one day since last confirmation</span>",
        "<span>faded = decaying, needs re-confirmation</span>",
        "<span>every field links to its source</span>",
        "</div>",
    ]

    order = list(CATEGORIES.keys()) + ["unclassified", "review"]
    for category in order:
        rows = buckets.get(category) or []
        if category in CATEGORIES:
            spec = CATEGORIES[category]
            label, buys, thesis = spec["label"], spec["buys"], spec["retention_thesis"]
        elif category == "review":
            label = "Review queue"
            buys = "not yet trusted"
            thesis = ("Machine-extracted below the confidence floor, or seen on a single launch "
                      "source with no corroboration. These do not enter the map until an analyst "
                      "confirms or kills them. Nothing here is a claim, it is a question.")
        else:
            label, buys, thesis = "Unclassified", "not yet placed", "queued for analyst review"
        delta_html = ""
        if category in momentum:
            delta = momentum[category]["delta"]
            cls = "up" if delta > 0 else ("down" if delta < 0 else "")
            delta_html = f'<span class="delta {cls}">{delta:+} vs baseline</span>'
        parts.append("<section class=band>")
        parts.append(
            f'<div class=bandhead><h2>{html.escape(label)}</h2>'
            f'<span class=buys>buys: {html.escape(buys)}</span>{delta_html}</div>'
        )
        parts.append(f"<p class=thesis>{html.escape(thesis)}</p>")
        if not rows:
            empty_copy = ("queue is clear, nothing is waiting on a human"
                          if category == "review"
                          else "no companies tracked in this category yet")
            parts.append(f'<p class=empty>{empty_copy}</p></section>')
            continue
        rows.sort(key=lambda kv: meeting_score(kv[0], kv[1]), reverse=True)
        parts.append("<div class=grid>")
        for key, entity in rows:
            days = _age_days(entity.get("last_seen", entity.get("first_seen", "")))
            weeks = max(1, min(14, days + 1))
            facts = entity.get("facts", {})
            stage = (facts.get("stage") or {}).get("value")
            amount = (facts.get("last_round_musd") or {}).get("value")
            region = (facts.get("region") or {}).get("value")
            events = entity.get("events", [])
            latest = events[-1] if events else None
            meta = []
            if _age_days(entity.get("first_seen", "")) <= 7:
                meta.append('<span class=new>new</span>')
            if stage:
                meta.append(html.escape(stage))
            if amount:
                meta.append(f"${amount}M")
            if region and region != "global":
                meta.append(html.escape(region))
            meta.append(f"{days}d")
            ticks = "".join('<span class=tick></span>' for _ in range(weeks))
            parts.append(f'<article class="card {_decay_class(days)}">')
            parts.append(f'<div class=gutter title="{days} days since last confirmation">{ticks}</div>')
            parts.append("<div>")
            parts.append(f'<div class=name>{html.escape(entity["name"])}</div>')
            parts.append(f'<div class=meta>{" ".join(meta)}</div>')
            if latest:
                parts.append(
                    f'<p class=headline><a href="{html.escape(latest["source_url"])}">'
                    f'{html.escape(latest["headline"][:130])}</a></p>'
                )
                parts.append(
                    f'<div class=prov>{html.escape(latest["source_id"])} &middot; '
                    f'{html.escape(latest["provenance"])} &middot; conf '
                    f'{latest.get("confidence") or "n/a"}</div>'
                )
            parts.append("</div></article>")
        parts.append("</div></section>")

    pressure = digest.get("thesis_under_pressure") or ""
    parts.append(
        "<footer>"
        f"<p>{html.escape(pressure)}</p>"
        "<p>Generated by the radar pipeline. Categories, stages and amounts are machine-extracted "
        "and carry a source link and a timestamp. Conviction, ranking and pass decisions stay with "
        "the analyst and are never written by the model.</p>"
        "</footer></div></body></html>"
    )

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(parts))
    return path
