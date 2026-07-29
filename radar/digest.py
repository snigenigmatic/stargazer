from collections import Counter
from datetime import datetime, timezone

from .taxonomy import CATEGORIES


def _age_days(iso):
    try:
        then = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return 999
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - then).days


REVIEW_CONFIDENCE = 0.7
UNCORROBORATED_SOURCES = {"producthunt", "hackernews"}


def needs_review(entity):
    events = entity.get("events", [])
    if not events:
        return True
    provenances = {e.get("provenance") for e in events}
    if "human" in provenances:
        return False
    confidence = max((e.get("confidence") or 0) for e in events)
    if confidence < REVIEW_CONFIDENCE:
        return True
    sources = {e.get("source_id") for e in events}
    if sources <= UNCORROBORATED_SOURCES and len(events) < 2:
        return True
    return False


def meeting_score(key, entity):
    score = 0.0
    facts = entity.get("facts", {})
    if _age_days(entity.get("first_seen", "")) <= 7:
        score += 3
    stage = (facts.get("stage") or {}).get("value")
    if stage in ("pre-seed", "seed", "series a"):
        score += 3
    amount = (facts.get("last_round_musd") or {}).get("value")
    if amount and amount <= 30:
        score += 2
    category = (facts.get("category") or {}).get("value")
    if category in ("relationship", "ambient", "agent"):
        score += 2
    if (facts.get("region") or {}).get("value") == "india":
        score += 1
    leading = sum(1 for e in entity.get("events", []) if e.get("source_id") in ("producthunt", "hackernews"))
    score += min(leading, 3)
    if entity.get("review", {}).get("status") == "passed":
        score -= 5
    return round(score, 1)


def category_momentum(store):
    now = Counter()
    prior = Counter()
    for entity in store.data["entities"].values():
        category = (entity.get("facts", {}).get("category") or {}).get("value")
        if not category:
            continue
        for event in entity.get("events", []):
            age = _age_days(event.get("published_at", ""))
            if age <= 7:
                now[category] += 1
            elif age <= 28:
                prior[category] += 1
    rows = []
    for key in CATEGORIES:
        recent = now[key]
        baseline = prior[key] / 3 if prior[key] else 0
        delta = recent - baseline
        rows.append({"category": key, "last7": recent, "weekly_baseline": round(baseline, 1), "delta": round(delta, 1)})
    rows.sort(key=lambda r: r["delta"], reverse=True)
    return rows


def build(store, changes, limit_changes=5, limit_meet=2):
    entities = store.data["entities"]
    funding = [c for c in changes if c["kind"] == "funding"]
    new = [c for c in changes if c["kind"] == "new_entity"]
    moved = [c for c in changes if c["kind"] == "field_changed"]

    headline_changes = []
    for change in sorted(funding, key=lambda c: c.get("amount_musd") or 0, reverse=True):
        entity = entities[change["entity"]]
        stage = change.get("stage") or "undisclosed stage"
        headline_changes.append(f'{entity["name"]} raised ${change["amount_musd"]}M ({stage})')
    for change in new:
        if len(headline_changes) >= limit_changes:
            break
        entity = entities[change["entity"]]
        category = (entity["facts"].get("category") or {}).get("value", "unclassified")
        headline_changes.append(f'{entity["name"]} entered the map under {category}')
    for change in moved:
        if len(headline_changes) >= limit_changes:
            break
        entity = entities[change["entity"]]
        headline_changes.append(
            f'{entity["name"]} moved {change["field"]} from {change["from"]} to {change["to"]}'
        )
    headline_changes = headline_changes[:limit_changes]

    touched = {c["entity"] for c in changes if not needs_review(entities[c["entity"]])}
    ranked = sorted(
        ((meeting_score(k, entities[k]), k) for k in touched),
        reverse=True,
    )
    to_meet = []
    for score, key in ranked[:limit_meet]:
        entity = entities[key]
        facts = entity["facts"]
        to_meet.append(
            {
                "name": entity["name"],
                "score": score,
                "category": (facts.get("category") or {}).get("value"),
                "stage": (facts.get("stage") or {}).get("value"),
                "why": _why(entity, score),
                "source": entity["events"][-1]["source_url"] if entity["events"] else None,
            }
        )

    momentum = category_momentum(store)
    pressure = _pressure(momentum)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "changed": headline_changes,
        "to_meet": to_meet,
        "momentum": momentum,
        "thesis_under_pressure": pressure,
        "counts": {
            "entities": len(entities),
            "changes": len(changes),
            "new": len(new),
            "funding": len(funding),
        },
    }


def _why(entity, score):
    facts = entity["facts"]
    bits = []
    if _age_days(entity.get("first_seen", "")) <= 7:
        bits.append("new to the map this week")
    stage = (facts.get("stage") or {}).get("value")
    if stage:
        bits.append(f"at {stage}")
    leading = [e for e in entity.get("events", []) if e.get("source_id") in ("producthunt", "hackernews")]
    if leading:
        bits.append("surfaced on a leading source before press coverage")
    category = (facts.get("category") or {}).get("value")
    if category in CATEGORIES:
        bits.append(CATEGORIES[category]["retention_thesis"])
    return "; ".join(bits) or "recent activity"


def _pressure(momentum):
    if not momentum:
        return None
    top = momentum[0]
    bottom = momentum[-1]
    if bottom["delta"] < 0:
        return (
            f'{CATEGORIES[bottom["category"]]["label"]} is going quiet '
            f'({bottom["last7"]} items in the last 7 days against a {bottom["weekly_baseline"]} weekly baseline) '
            f'while {CATEGORIES[top["category"]]["label"]} accelerates. '
            "If the fund has an active thesis in the first, it needs a reason that is not momentum."
        )
    return (
        f'{CATEGORIES[top["category"]]["label"]} is absorbing attention this week. '
        "Crowding is a reason to move earlier, not a reason to believe."
    )


def to_markdown(digest):
    lines = [
        f'# Consumer AI radar, week of {digest["generated_at"][:10]}',
        "",
        f'{digest["counts"]["entities"]} companies tracked, {digest["counts"]["changes"]} changes this run, '
        f'{digest["counts"]["new"]} new.',
        "",
        "## What changed",
        "",
    ]
    for i, item in enumerate(digest["changed"], 1):
        lines.append(f"{i}. {item}")
    if not digest["changed"]:
        lines.append("_Nothing moved._")
    lines += ["", "## Worth a meeting", ""]
    for item in digest["to_meet"]:
        lines.append(f'**{item["name"]}** ({item["category"] or "unclassified"}, score {item["score"]})')
        lines.append(f'  {item["why"]}')
        if item["source"]:
            lines.append(f'  {item["source"]}')
        lines.append("")
    if not digest["to_meet"]:
        lines.append("_No new names cleared the bar._\n")
    lines += ["## Category momentum", "", "| Category | Last 7d | Weekly baseline | Delta |", "| --- | --- | --- | --- |"]
    for row in digest["momentum"]:
        lines.append(
            f'| {CATEGORIES[row["category"]]["label"]} | {row["last7"]} | {row["weekly_baseline"]} | {row["delta"]:+} |'
        )
    lines += ["", "## Thesis under pressure", "", digest["thesis_under_pressure"] or "_Not enough history yet._", ""]
    return "\n".join(lines)
