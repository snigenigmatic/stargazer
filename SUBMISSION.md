# Consumer AI: a map, and a system to keep it true

Kaustubh C
c-kaustubh.netlify.app | github.com/snigenigmatic

---

## Part 1: Market mapping

### The categorisation

Most consumer AI maps sort by output type: chat, image, video, music, search. That is a
screenshot of the app store, not a thesis. It tells you what a company makes and nothing
about whether it will still have users in eighteen months.

I sorted by **what the user is actually buying**, because that determines how much of the
value stays inside the product after the session ends.

| Company | What the user buys | Category |
| --- | --- | --- |
| OpenAI (ChatGPT) | a default place to think | Surface |
| Perplexity | a correct answer | Answer engine |
| Suno | a finished artifact | Creation tool |
| Character.AI | the presence of another mind | Relationship |
| Sesame | a system that already knows you | Ambient context |

The axis running underneath: **how much of the value is retained by the product versus
handed back to the user.**

Suno gives you the song and you leave. Nothing accumulates. If a better model ships next
month, your catalogue does not hold you. Character.AI keeps the exact thing you came for,
and that thing was built by you over months. Perplexity sits in the middle and has to
defend on speed and trust, because the answer itself walks out the door.

This is not a claim that creation tools are bad businesses. It is a claim that they are
**distribution and taste businesses wearing AI clothing**, and should be underwritten that
way rather than as software with compounding retention.

### Patterns

**1. Consumer AI sells hard and sticks badly.**
RevenueCat's 2026 report, across roughly a billion transactions, found AI apps convert
trials about 52% better than non-AI apps, while annual retention sits at 21.1% against
30.7%. Higher revenue per user, faster churn. The category is currently monetising
curiosity, not habit. Every diligence conversation should start at month four, not at the
top of the funnel.

**2. The capital is barbell shaped, and the top half is not investable at seed.**
PitchBook put consumer AI at roughly $89B in 2025, but ten billion-dollar-plus raises
accounted for about $71.5B of that. Strip those out and the real market is around $17.5B.
Median round size fell from about $43M to about $15M while average round size rose. A seed
fund is not competing with the megadeals. It is fishing in a pool that is getting more
crowded and cheaper per company.

**3. Category leadership rotates faster than a map can be maintained by hand.**
AI search took roughly 71% of consumer AI capital in 2025. Content creation took roughly
75% year to date in 2026. That is a full rotation in four quarters. Any map built as a
document is wrong within two quarters of being written, which is the entire argument for
Part 2.

**4. Where the moat exists, it is accumulated rather than trained.**
Nobody in this category has a model advantage that survives a quarter. The companies with
real retention have something the user built and cannot export: a relationship, a memory,
a graph, a workflow. That is the filter I would run every consumer AI deal through.

### One to explore further: Sesame

Sesame is the only company in this set where the asset that retains the user is created by
the user and cannot be taken anywhere else. Voice plus persistent memory is the first
consumer AI form factor where switching costs feel like a loss rather than a settings
change, which is exactly what pattern 1 says the category is missing.

What I would want to test in a first call:

- Cost per engaged minute, and whether it falls faster than usage grows. Voice is the most
  expensive modality to serve and the easiest to over-consume.
- Whether the hardware is the wedge or the distraction. Ambient context needs to be always
  present, but hardware turns a software margin into an inventory business.
- Day 30 and day 90 conversation depth, not DAU. If memory is the moat, depth should rise
  with tenure. If it is flat, the memory is decorative.

The reason to look now rather than later is that this is the one category where being early
matters, because the moat is built by users over time and a competitor cannot buy it back.

---

## Part 2: Keeping the map true

### The core design decision

A market map should be a **view, not a document**. Almost every attempt at this fails the
same way: someone builds a scraper that writes into a Notion page, the page is beautiful for
three weeks, and then nobody trusts it because no one can tell which lines are current.

So the system keeps three layers separate:

- **Events.** A round closed, a product shipped, a founder left, an app moved 40 places in
  the store rankings. Immutable, timestamped, always carrying a source URL.
- **Entities.** The deduplicated company. Every field is a fact object, not a value:
  `{value, source_url, observed_at, provenance, confidence}`. A company does not have a
  category, it has a category that something claimed on a date.
- **Judgments.** Our category conviction, our pass reason, our meeting notes.

Only the third layer is the fund's actual IP, and it is the only layer a model never writes
to. The map itself is then just a rendering of layers one and two, filtered by layer three.

### Where the data comes from

Ordered by how early the signal fires, which is the only ordering that matters:

**Leading.** Hiring pages and LinkedIn headcount (a company staffing a growth team is
raising in two months), GitHub and Discord activity, Product Hunt, app store rank and
review velocity, App Annie or Appfigures style download curves.

**Coincident.** X and founder posts, waitlist and pricing page changes, podcast appearances.

**Lagging.** Crunchbase, Tracxn, PitchBook, press. By the time TechCrunch writes it, the
round is closed and the meeting you wanted happened four months ago.

**Proprietary.** The fund's own CRM, call notes, founder intros, portfolio company chatter.
This is the only source no competing fund has, and in practice it should be weighted
highest.

For an India-focused fund I would add Entrackr, Inc42, YourStory and MCA filings, since
Indian rounds frequently appear in registry filings before they appear in press.

### Where AI fits, and where it does not

**AI does:**

- Extraction. Turn a messy paragraph into structured fields.
- Entity resolution. The same company appears as "Character.AI", "Character AI",
  "c.ai" and "Character Technologies Inc". This is the single biggest source of rot in
  hand-maintained maps.
- Classification into the taxonomy, with a confidence score and a one-line reason.
- Change detection and synthesis. What is different this week, and does it contradict
  something we believed.
- Retrieval. An analyst asks "who is building voice companions in India at seed" in plain
  English and gets an answer with sources.

**AI does not:**

- Decide what matters. Ranking and conviction stay human.
- Write into the judgments layer.
- Assert a fact without a source link. Anything the model produces that cannot be traced
  back to a URL goes to a review queue instead of the map.

Cost discipline: a cheap model does per-item classification at volume, an expensive model
does the weekly synthesis only. Classification is the high-volume, low-stakes call, so it
should never run on the expensive model.

### The output

Three surfaces, one underlying store:

1. **The live map.** Categories as bands, companies as cards, every field carrying its
   source and its age. Facts visibly decay as they get stale, so the map tells you what it
   no longer knows instead of quietly lying. The decay clock runs in days, not weeks,
   because in a market that rotates categories in four quarters a week-old fact is already
   a guess.
2. **A Friday digest.** Five things that changed, two companies worth a meeting with a
   reason attached, one thesis under pressure. Short enough that partners actually read it.
3. **A Slack query layer.** Ask the map a question, get an answer with citations.

### The metric

The system is working if the fund's first meeting with a company happens **before the round
is announced**. Everything else is decoration. Number of companies tracked is a vanity
metric and will get gamed by whoever maintains it.

---

## The prototype

I built a working version rather than describing one. It runs against live sources.

```
python run.py --seed seed.json    # once, to load the analyst watchlist
python run.py                     # every run after that
```

It pulls six live feeds (TechCrunch, TechCrunch AI, VentureBeat, YourStory, Product Hunt,
Hacker News), extracts candidate consumer AI events, resolves them against existing
entities, applies them to a timestamped fact store, diffs against the previous run, and
emits the map and the digest.

On the run this submission is built from it surfaced Polar (an AI browser from an
ex-Perplexity engineer, seed, published that morning), Fish Audio at a $52M seed, and Hint,
a home assistant co-founded by Martha Stewart. Three leads out of one pass over public RSS,
which is the weakest source tier in the design.

Four things in it are deliberate and worth pointing at:

**Nothing enters the map without clearing a floor.** Anything below 0.7 confidence goes to
a review queue, and so does anything seen once on a launch-only source like Product Hunt
with no corroboration. On a typical run that holds back roughly a dozen cards against
twenty on the map. The queue is not a disclaimer, it is the working surface: those are
questions for an analyst, not claims.

**Companies the fund cannot invest in are filtered out entirely.** Google and Meta kept
getting extracted as consumer AI companies, which is technically correct and useless. A
seed fund's map should only contain things it can act on.

**The extraction layer is pluggable and degrades honestly.** With an API key it uses an LLM.
Without one it falls back to rules, and rule output is capped below the confidence floor so
it can never reach the map on its own. Rules cannot do entity extraction on prose. Rather
than tune that away I made the ceiling explicit, because the honest version of "where does
AI fit" is a layer where the alternative genuinely does not work.

**Judgment overrides the machine, not the other way round.** Analyst-entered entities carry
provenance `human` and bypass the confidence gate. A human can promote something out of the
review queue or kill it, and that decision is durable.

### Known limitations

**The confidence floor is a blunt instrument.** It catches things the model was unsure
about, not things the model was confidently wrong about. On the attached render Ozlo, a
sleep earbud, cleared the floor at 0.7 and sits in Ambient context. It should not be there.
A threshold cannot fix a category error, which is exactly why the analyst override exists
and why ranking never leaves the human layer.

**Entity resolution splits on version suffixes.** The same product has appeared as `EQK`
and `EQK 3.0` across runs, because the model returned a different name each time and the
fuzzy match did not close the gap. It resolves on a fresh store and reappears as the store
accumulates, which is the worst kind of bug: intermittent and invisible until the map is
already trusted. The fix is a normalisation pass stripping trailing version tokens before
matching.

**Encoding.** Headlines carrying smart quotes round-trip badly on Windows, where Python's
default file encoding is the system codepage rather than UTF-8. Visible on the Ozlo and
Qwen Scribe cards in the attached render. Every read and write needs an explicit
`encoding="utf-8"`, and a store written before that fix carries the damage forward.

**No eval set.** Classification quality is currently assessed by reading the output, which
does not scale and does not catch drift. Fifty hand-labelled articles run on every prompt
change would.

**RSS is a lagging source** and is here for convenience, not because it is the right one.

---

Sources: RevenueCat State of Subscription Apps 2026, PitchBook Q1 2026 analyst note on
consumer AI, New Market Pitch consumer AI funding trends 2026.
