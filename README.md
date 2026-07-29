# radar

A working prototype of a continuously updated consumer AI market map for a venture fund.

The design decision the whole thing rests on: **a market map is a view, not a document.**
Events are immutable and timestamped, entities are deduplicated bundles of facts that each
carry a source and an age, and analyst judgment is a separate layer no model writes to.

## Run it

```bash
pip install feedparser
python run.py --seed seed.json      # first run, loads the analyst watchlist
python run.py                       # every run after that
python run.py --no-llm              # force the rules fallback
```

With `ANTHROPIC_API_KEY` set, extraction and classification run on an LLM. Without it, the
pipeline falls back to rules and routes anything low-confidence into a review queue.

## Output

- `out/map.html` the live map, grouped by category, with visible decay on stale facts
- `out/digest.md` the Friday digest: what changed, who to meet, what thesis is under pressure
- `out/digest.json` the same, machine readable
- `store/map.json` the fact store, one entry per entity, every field with provenance

## Layout

```
radar/taxonomy.py   the categorisation and its keyword seeds
radar/sources.py    feed pullers, each record tagged leading or lagging
radar/extract.py    relevance gate, rules extractor, LLM extractor, same schema
radar/entities.py   entity resolution and the timestamped fact store
radar/digest.py     change detection, meeting score, category momentum
radar/render.py     the HTML view
```

## Known limits

RSS is a lagging source and is here for convenience. The real signal is in hiring pages,
app store rank and the fund's own CRM. The rules extractor is deliberately left untuned so
its failure modes are visible.
