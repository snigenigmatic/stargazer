import json
import os
import re
import urllib.request

from .taxonomy import AI_SIGNALS, CATEGORIES, CONSUMER_SIGNALS, ENTERPRISE_SIGNALS, STAGES

MONEY = re.compile(r"\$\s?([\d,.]+)\s?(billion|million|bn|mn|m\b|b\b|k\b)", re.I)
RAISE_VERBS = r"(raises?|raised|secures?|lands?|closes?|bags?|nets?|picks up)"
LAUNCH_VERBS = r"(launches?|launched|unveils?|ships?|releases?|introduces?|debuts?)"
COMPANY_HEAD = re.compile(r"^([A-Z][\w.&'\-]*(?:\s+[A-Z][\w.&'\-]*){0,3})\s+" + RAISE_VERBS, re.I)
COMPANY_LAUNCH = re.compile(r"^([A-Z][\w.&'\-]*(?:\s+[A-Z][\w.&'\-]*){0,3})\s+" + LAUNCH_VERBS, re.I)

NOISE_HEADS = {
    "the", "a", "an", "how", "why", "what", "this", "these", "here", "meet",
    "exclusive", "report", "opinion", "watch", "video", "podcast", "daily",
}


def _score(text, words):
    low = text.lower()
    total = 0
    for word in words:
        if re.search(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])", low):
            total += 1
    return total


def relevance(record):
    text = f"{record['title']} {record['summary']}"
    ai = _score(text, AI_SIGNALS)
    consumer = _score(text, CONSUMER_SIGNALS)
    enterprise = _score(text, ENTERPRISE_SIGNALS)
    score = (ai * 2) + (consumer * 2) - (enterprise * 3)
    return score, {"ai": ai, "consumer": consumer, "enterprise": enterprise}


def classify(text):
    low = text.lower()
    scored = []
    for key, spec in CATEGORIES.items():
        hits = [w for w in spec["keywords"]
                if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", low)]
        if hits:
            scored.append((len(hits), key, hits))
    if not scored:
        return None, 0.0, []
    scored.sort(reverse=True)
    top = scored[0]
    total = sum(s[0] for s in scored)
    return top[1], round(top[0] / total, 2), top[2]


def parse_money(text):
    match = MONEY.search(text)
    if not match:
        return None
    raw = match.group(1).replace(",", "")
    try:
        value = float(raw)
    except ValueError:
        return None
    unit = match.group(2).lower()
    if unit.startswith("b"):
        value *= 1000
    elif unit.startswith("k"):
        value /= 1000
    return round(value, 2)


def parse_stage(text):
    low = text.lower()
    for stage in STAGES:
        if stage in low:
            return stage
    return None


PROPER = re.compile(r"\b([A-Z][a-zA-Z0-9.&'\-]*(?:\s+(?:[A-Z][a-zA-Z0-9.&'\-]*|AI|Labs))*)")

STOP_PROPER = {
    "ai", "the", "a", "an", "us", "uk", "eu", "china", "chinese", "india", "indian",
    "openai", "google", "meta", "apple", "microsoft", "amazon", "nvidia", "anthropic",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december", "new", "why", "how", "what",
    "this", "these", "here", "meet", "exclusive", "report", "opinion", "watch",
    "video", "podcast", "daily", "week", "today", "silicon valley", "wall street",
    "techcrunch", "product hunt", "hacker news", "yc", "y combinator",
}

BIG_TECH = {
    "google", "alphabet", "meta", "meta ai", "facebook", "apple", "amazon",
    "microsoft", "nvidia", "bytedance", "tiktok", "snap", "twitter", "x",
    "samsung", "tesla", "ibm", "oracle", "salesforce", "adobe", "spotify",
}

GAZETTEER = {
    "perplexity", "suno", "udio", "character.ai", "replika", "sesame", "elevenlabs",
    "runway", "luma", "pika", "higgsfield", "synthesia", "captions", "genspark",
    "you.com", "astrocade", "town", "midjourney", "cursor", "granola", "limitless",
    "rabbit", "humane", "friend", "tolan", "portola", "krea", "hedra", "descript",
    "opus clip", "photoroom", "lovable", "bolt", "poke", "cognition", "krutrim",
    "sarvam", "sarvam ai", "dashtoon", "wysa", "sahaay", "gnani",
}


def guess_company(title):
    low = title.lower()
    for name in GAZETTEER:
        if re.search(r"(?<![a-z])" + re.escape(name) + r"(?![a-z])", low):
            return name.title() if name.islower() else name
    for pattern in (COMPANY_HEAD, COMPANY_LAUNCH):
        match = pattern.match(title)
        if match:
            name = match.group(1).strip()
            if name.split()[0].lower() in NOISE_HEADS:
                continue
            return name
    trigger = re.search(RAISE_VERBS + "|" + LAUNCH_VERBS, title, re.I)
    candidates = []
    for match in PROPER.finditer(title):
        name = match.group(1).strip().rstrip("'s").strip()
        if not name or name.lower() in STOP_PROPER:
            continue
        if len(name) < 3 or name.isupper() and len(name) > 5:
            continue
        if name.split()[0].lower() in NOISE_HEADS:
            continue
        distance = abs(match.start() - trigger.start()) if trigger else match.start()
        candidates.append((distance, match.start(), name))
    if not candidates:
        return None
    candidates.sort()
    return candidates[0][2]


def _corroborated(name, record):
    low_name = name.lower()
    if low_name in GAZETTEER:
        return True
    blob = f"{record['title']} {record['summary']}".lower()
    occurrences = len(re.findall(r"(?<![a-z])" + re.escape(low_name) + r"(?![a-z])", blob))
    return occurrences >= 2


def rule_extract(record):
    text = f"{record['title']} {record['summary']}"
    score, parts = relevance(record)
    if score < 3:
        return None
    company = guess_company(record["title"])
    if not company or not _corroborated(company, record):
        return None
    category, confidence, hits = classify(text)
    if not category:
        return None
    amount = parse_money(text)
    return {
        "company": company,
        "category": category,
        "category_confidence": min(confidence, 0.6),
        "category_evidence": hits,
        "event_type": "funding" if amount else "product",
        "amount_musd": amount,
        "stage": parse_stage(text),
        "region": record["region"],
        "relevance": score,
        "relevance_parts": parts,
        "provenance": "rule",
        "source_url": record["url"],
        "source_id": record["source_id"],
        "observed_at": record["collected_at"],
        "published_at": record["published_at"],
        "headline": record["title"],
    }


PROMPT = """You are an analyst at a seed-stage venture fund maintaining a consumer AI market map.

Read the news items below. Return ONLY a JSON array, no prose, no markdown fences.

Include an item ONLY if it is about a company selling AI to individual people. Exclude
infrastructure, chips, enterprise software, model research and pure funding-market commentary.

For each included item return:
{"company": str, "category": one of %s, "category_confidence": 0-1 float,
 "reasoning": str (max 20 words), "event_type": "funding"|"product"|"launch"|"other",
 "amount_musd": float or null, "stage": str or null, "index": int}

Category definitions (what the user is buying):
%s

News items:
%s"""


def _catalogue():
    lines = []
    for key, spec in CATEGORIES.items():
        lines.append(f'- {key}: {spec["buys"]}')
    return "\n".join(lines)


def llm_extract(records, model="claude-sonnet-4-6", batch=25):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    results = []
    for start in range(0, len(records), batch):
        chunk = records[start : start + batch]
        listing = "\n".join(
            f'{i}. [{r["source_id"]}] {r["title"]} :: {r["summary"][:220]}'
            for i, r in enumerate(chunk)
        )
        body = json.dumps(
            {
                "model": model,
                "max_tokens": 4000,
                "messages": [
                    {
                        "role": "user",
                        "content": PROMPT
                        % (list(CATEGORIES.keys()), _catalogue(), listing),
                    }
                ],
            }
        ).encode()
        request = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "content-type": "application/json",
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read())
        except Exception:
            continue
        text = "".join(b.get("text", "") for b in payload.get("content", []))
        text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            continue
        for item in parsed:
            index = item.get("index")
            if not isinstance(index, int) or index >= len(chunk):
                continue
            if item.get("category") not in CATEGORIES:
                continue
            record = chunk[index]
            results.append(
                {
                    "company": item.get("company", "").strip(),
                    "category": item["category"],
                    "category_confidence": float(item.get("category_confidence") or 0.5),
                    "category_evidence": [item.get("reasoning", "")],
                    "event_type": item.get("event_type", "other"),
                    "amount_musd": item.get("amount_musd"),
                    "stage": item.get("stage"),
                    "region": record["region"],
                    "relevance": relevance(record)[0],
                    "relevance_parts": relevance(record)[1],
                    "provenance": "llm",
                    "source_url": record["url"],
                    "source_id": record["source_id"],
                    "observed_at": record["collected_at"],
                    "published_at": record["published_at"],
                    "headline": record["title"],
                }
            )
    return results


def _investable(event):
    return event.get("company", "").strip().lower() not in BIG_TECH


def extract(records, use_llm=True):
    if use_llm:
        llm = llm_extract(records)
        if llm is not None:
            return [e for e in llm if _investable(e)], "llm"
    events = [e for e in (rule_extract(r) for r in records) if e]
    return [e for e in events if _investable(e)], "rule"
