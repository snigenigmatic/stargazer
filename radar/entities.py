import difflib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

SUFFIXES = [
    "inc", "inc.", "llc", "ltd", "limited", "corp", "corporation", "labs", "lab",
    "technologies", "technology", "systems", "co", "company", "ai", "app", "io",
]


def slugify(name):
    base = re.sub(r"[^a-z0-9\s]", " ", name.lower())
    tokens = [t for t in base.split() if t and t not in SUFFIXES]
    if not tokens:
        tokens = base.split()
    return "-".join(tokens)


def normalise(name):
    return slugify(name).replace("-", " ")


class Store:
    def __init__(self, path):
        self.path = Path(path)
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = {"entities": {}, "runs": []}

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, sort_keys=True), encoding="utf-8")

    def match(self, name, threshold=0.86):
        slug = slugify(name)
        if slug in self.data["entities"]:
            return slug
        target = normalise(name)
        best, best_ratio = None, 0.0
        for key, entity in self.data["entities"].items():
            candidates = [normalise(entity["name"])] + [normalise(a) for a in entity.get("aliases", [])]
            for candidate in candidates:
                ratio = difflib.SequenceMatcher(None, target, candidate).ratio()
                if ratio > best_ratio:
                    best, best_ratio = key, ratio
        if best_ratio >= threshold:
            return best
        return None

    def _fact(self, value, event):
        return {
            "value": value,
            "source_url": event["source_url"],
            "source_id": event["source_id"],
            "observed_at": event["observed_at"],
            "provenance": event["provenance"],
        }

    def apply(self, event):
        name = event["company"]
        if not name:
            return None
        key = self.match(name)
        changes = []
        if key is None:
            key = slugify(name)
            self.data["entities"][key] = {
                "name": name,
                "aliases": [],
                "first_seen": event["observed_at"],
                "facts": {},
                "events": [],
                "review": {"status": "unreviewed", "note": None},
            }
            changes.append({"kind": "new_entity", "entity": key, "name": name})
        entity = self.data["entities"][key]
        if name != entity["name"] and name not in entity["aliases"]:
            entity["aliases"].append(name)

        for field in ("category", "stage", "region"):
            value = event.get(field)
            if value is None:
                continue
            current = entity["facts"].get(field)
            if current is None:
                entity["facts"][field] = self._fact(value, event)
                if field == "category":
                    changes.append({"kind": "categorised", "entity": key, "to": value})
            elif current["value"] != value:
                changes.append(
                    {"kind": "field_changed", "entity": key, "field": field,
                     "from": current["value"], "to": value}
                )
                entity["facts"].setdefault("_history", [])
                entity["facts"][field] = self._fact(value, event)

        if event.get("amount_musd"):
            entity["facts"]["last_round_musd"] = self._fact(event["amount_musd"], event)
            changes.append(
                {"kind": "funding", "entity": key, "amount_musd": event["amount_musd"],
                 "stage": event.get("stage")}
            )

        fingerprint = event["source_url"]
        if all(e["source_url"] != fingerprint for e in entity["events"]):
            entity["events"].append(
                {
                    "headline": event["headline"],
                    "event_type": event["event_type"],
                    "source_url": event["source_url"],
                    "source_id": event["source_id"],
                    "published_at": event["published_at"],
                    "observed_at": event["observed_at"],
                    "provenance": event["provenance"],
                    "confidence": event.get("category_confidence"),
                    "evidence": event.get("category_evidence", []),
                }
            )
        entity["last_seen"] = event["observed_at"]
        return changes

    def ingest(self, events):
        all_changes = []
        for event in events:
            changes = self.apply(event)
            if changes:
                all_changes.extend(changes)
        self.data["runs"].append(
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "events": len(events),
                "changes": len(all_changes),
            }
        )
        return all_changes
