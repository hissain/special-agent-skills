#!/usr/bin/env python3
"""
search_brave.py — Brave Search API client (requires free API key)

Usage:
    export BRAVE_API_KEY="your_key_here"
    python3 search_brave.py "query here" [--max N] [--json] [--freshness pw]

Free tier: 2,000 queries/month — sign up at https://brave.com/search/api/

Output:
    Human-readable list or JSON array of {title, url, snippet, age}.

Requires: python3 stdlib only (urllib, json)
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request


# ---------------------------------------------------------------------------
# Brave Search API wrapper
# ---------------------------------------------------------------------------

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

VALID_FRESHNESS = {"pd", "pw", "pm", "py"}  # day, week, month, year


def search_brave(
    query: str,
    max_results: int = 10,
    freshness: str | None = None,
    country: str = "US",
    lang: str = "en",
    api_key: str | None = None,
) -> list[dict]:
    """
    Query the Brave Search API.

    Args:
        query: Search query string.
        max_results: Max results (1–20 per Brave API limits).
        freshness: Date filter — 'pd' (day), 'pw' (week), 'pm' (month), 'py' (year).
        country: Country code, e.g. 'US', 'GB'.
        lang: Language code, e.g. 'en', 'fr'.
        api_key: Brave API key. Falls back to BRAVE_API_KEY env var.

    Returns:
        List of dicts with keys: title, url, snippet, age.
    """
    key = api_key or os.environ.get("BRAVE_API_KEY", "")
    if not key:
        print(
            "[search_brave] ERROR: No API key found.\n"
            "  Set BRAVE_API_KEY environment variable or pass --api-key.\n"
            "  Get a free key at https://brave.com/search/api/",
            file=sys.stderr,
        )
        return []

    params: dict[str, str] = {
        "q": query,
        "count": str(min(max_results, 20)),
        "country": country,
        "search_lang": lang,
        "safesearch": "moderate",
    }
    if freshness and freshness in VALID_FRESHNESS:
        params["freshness"] = freshness

    url = f"{BRAVE_SEARCH_URL}?{urllib.parse.urlencode(params)}"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": key,
    }

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            # Handle gzip — urllib handles it transparently when Accept-Encoding is set
            # but the response isn't automatically decompressed in all versions
            raw = resp.read()
            encoding = resp.headers.get_content_charset("utf-8")
            # Try gzip decompression
            try:
                import gzip
                raw = gzip.decompress(raw)
            except Exception:
                pass  # Not gzip or already decoded
            data = json.loads(raw.decode(encoding, errors="replace"))
    except urllib.error.HTTPError as exc:
        print(f"[search_brave] HTTP error: {exc.code} {exc.reason}", file=sys.stderr)
        if exc.code == 401:
            print("  → Invalid or expired API key.", file=sys.stderr)
        elif exc.code == 429:
            print("  → Rate limit exceeded.", file=sys.stderr)
        return []
    except Exception as exc:
        print(f"[search_brave] Request failed: {exc}", file=sys.stderr)
        return []

    results = []
    for item in data.get("web", {}).get("results", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": item.get("description", ""),
            "age": item.get("age", ""),
        })
    return results


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def print_human(results: list[dict]) -> None:
    if not results:
        print("No results found.")
        return
    for i, r in enumerate(results, 1):
        age = f" [{r['age']}]" if r.get("age") else ""
        print(f"[{i}]{age} {r['title']}")
        print(f"    {r['url']}")
        if r["snippet"]:
            print(f"    {r['snippet'][:200]}")
        print()


def print_json(results: list[dict]) -> None:
    print(json.dumps(results, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search using Brave Search API (requires free API key).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("query", help="Search query string")
    parser.add_argument(
        "--max", type=int, default=10, metavar="N",
        help="Maximum number of results (1–20, default: 10)"
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Output results as JSON array"
    )
    parser.add_argument(
        "--freshness",
        choices=["pd", "pw", "pm", "py"],
        default=None,
        help="Date filter: pd=day, pw=week, pm=month, py=year"
    )
    parser.add_argument(
        "--country", default="US",
        help="Country code, e.g. US, GB (default: US)"
    )
    parser.add_argument(
        "--lang", default="en",
        help="Language code, e.g. en, fr (default: en)"
    )
    parser.add_argument(
        "--api-key", default=None, dest="api_key",
        help="Brave API key (overrides BRAVE_API_KEY env var)"
    )
    args = parser.parse_args()

    results = search_brave(
        args.query,
        max_results=args.max,
        freshness=args.freshness,
        country=args.country,
        lang=args.lang,
        api_key=args.api_key,
    )

    if args.json_output:
        print_json(results)
    else:
        print_human(results)


if __name__ == "__main__":
    main()
