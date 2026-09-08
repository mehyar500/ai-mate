"""Save public catalog metadata, not vendor descriptions. No credentials needed."""
import concurrent.futures
import datetime
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = "https://developers.cloudflare.com/workers-ai/models/"


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "AmorienCatalogAudit/1.0 (public documentation research)"})
    with urllib.request.urlopen(request, timeout=40) as response:
        return response.read().decode("utf-8")


def extract(url):
    page = fetch(url + "index.md")
    model = re.search(r"`(@(?:cf|hf)/[^`\s]+)`", page)
    if not model:
        raise ValueError(f"No model ID: {url}")
    task = re.search(r"^([^\n]+) • ([^\n]+)$", page, re.M)
    price = re.search(r"^\| Unit Pricing\s*\|([^\n]+)", page, re.M)
    context = re.search(r"^\| Context Window[^\n]*?\|\s*([^|]+)", page, re.M)
    return {
        "id": model[1],
        "task": task[1].strip() if task else "unclassified",
        "author": task[2].strip() if task else "unclassified",
        "deprecated": bool(re.search(r"^\* Deprecated", page, re.M)),
        "context": context[1].strip() if context else None,
        "display_price": price[1].strip().rstrip("|").strip() if price else None,
        "source": url,
    }


def main():
    catalog = fetch(CATALOG + "index.md")
    urls = sorted(set(re.findall(r"https://developers\.cloudflare\.com/workers-ai/models/[A-Za-z0-9_.-]+/", catalog)))
    expected = re.search(r"We found (\d+) models", catalog)
    if not expected or len(urls) != int(expected[1]):
        raise ValueError(f"Catalog format/count changed: {len(urls)} links")
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        models = sorted(pool.map(extract, urls), key=lambda row: row["id"])
    if len({m["id"] for m in models}) != len(models):
        raise ValueError("Duplicate model IDs")
    data = {
        "retrieved_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source": CATALOG,
        "scope": "All model detail links on Workers AI hosted catalog; includes deprecated entries. Not every world model or AI Gateway provider. Display prices may be rounded; use platform pricing for budgets. Listing is not a license or availability test.",
        "count": len(models),
        "models": models,
    }
    dest = ROOT / "docs/research/cloudflare-models.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(models)} models to {dest.relative_to(ROOT)}")
    print(json.dumps({t: sum(m["task"] == t for m in models) for t in sorted({m["task"] for m in models})}))


if __name__ == "__main__":
    main()
