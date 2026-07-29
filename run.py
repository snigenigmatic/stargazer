from marshal import load
import argparse
import json
from pathlib import Path

from radar import digest as digest_mod
from radar import render as render_mod
from radar import sources
from radar.entities import Store
from radar.extract import extract
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Consumer AI market map radar")
    parser.add_argument("--store", default="store/map.json")
    parser.add_argument("--out", default="out")
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--seed", default=None)
    args = parser.parse_args()

    store = Store(args.store)

    if args.seed:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        seeds = json.loads(Path(args.seed).read_text())
        for entry in seeds:
            store.apply({
                "company": entry["company"],
                "category": entry["category"],
                "category_confidence": 1.0,
                "category_evidence": [entry.get("note", "")],
                "event_type": "watchlist",
                "amount_musd": None,
                "stage": None,
                "region": entry.get("region", "global"),
                "provenance": "human",
                "source_url": "analyst://watchlist",
                "source_id": "watchlist",
                "observed_at": now,
                "published_at": now,
                "headline": entry.get("note", "added to watchlist by analyst"),
            })
        store.save()
        print(f"seeded {len(seeds)} watchlist entities")

    records, errors = sources.fetch_all()
    print(f"fetched {len(records)} records from {len(sources.FEEDS)} sources")
    for err in errors:
        print(f"  source error: {err['source_id']}: {err['error'][:80]}")

    events, mode = extract(records, use_llm=not args.no_llm)
    print(f"extracted {len(events)} candidate events via {mode} extractor")

    changes = store.ingest(events)
    store.save()
    print(f"{len(changes)} changes applied, {len(store.data['entities'])} entities tracked")

    result = digest_mod.build(store, changes)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "digest.md").write_text(digest_mod.to_markdown(result), encoding="utf-8")
    (out / "digest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    render_mod.render(store, result, out / "map.html")
    print(f"wrote {out}/digest.md, {out}/digest.json, {out}/map.html")


if __name__ == "__main__":
    main()
