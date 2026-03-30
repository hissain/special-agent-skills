#!/usr/bin/env python3
"""
search_ddg.py — DuckDuckGo Lite web search (no API key required)

Usage:
    python3 search_ddg.py "query here" [--max N] [--json] [--delay SECONDS]

Output:
    Human-readable list or JSON array of {title, url, snippet}.

Requires: python3 stdlib only (urllib, html.parser)
"""

import argparse
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser


# ---------------------------------------------------------------------------
# HTML Parser — extracts search results from DDG Lite response
# ---------------------------------------------------------------------------

class DDGLiteParser(HTMLParser):
    """Parse DuckDuckGo Lite HTML to extract result titles, URLs, snippets."""

    def __init__(self):
        super().__init__()
        self.results: list[dict] = []
        self._in_result_title = False
        self._in_result_snippet = False
        self._current: dict | None = None
        self._depth = 0
        self._tag_stack: list[str] = []

    # --- helpers ---
    def _attr(self, attrs: list, name: str) -> str:
        for k, v in attrs:
            if k == name:
                return v or ""
        return ""

    # --- parser callbacks ---
    def handle_starttag(self, tag: str, attrs: list):
        self._tag_stack.append(tag)
        cls = self._attr(attrs, "class")
        href = self._attr(attrs, "href")

        # DDG Lite result structure:
        #   <a class="result-link" href="..."> TITLE </a>
        #   <td class="result-snippet"> SNIPPET </td>
        if tag == "a" and "result-link" in cls and href:
            url = href
            # DDG sometimes wraps URLs — unwrap uddg= redirects
            if "uddg=" in url:
                try:
                    parsed = urllib.parse.urlparse(url)
                    params = urllib.parse.parse_qs(parsed.query)
                    url = params.get("uddg", [url])[0]
                    url = urllib.parse.unquote(url)
                except Exception:
                    pass
            self._current = {"title": "", "url": url, "snippet": ""}
            self._in_result_title = True

        elif tag == "td" and "result-snippet" in cls and self._current:
            self._in_result_snippet = True

    def handle_endtag(self, tag: str):
        if self._tag_stack:
            self._tag_stack.pop()
        if tag == "a" and self._in_result_title:
            self._in_result_title = False
            # Only commit result when we have a non-empty title
            if self._current and self._current["title"].strip():
                pass  # snippet may come after — will commit in snippet end
        if tag == "td" and self._in_result_snippet:
            self._in_result_snippet = False
            if self._current:
                self._current["title"] = html.unescape(self._current["title"]).strip()
                self._current["snippet"] = html.unescape(self._current["snippet"]).strip()
                if self._current["title"] and self._current["url"]:
                    self.results.append(self._current)
                self._current = None

    def handle_data(self, data: str):
        if self._in_result_title and self._current is not None:
            self._current["title"] += data
        elif self._in_result_snippet and self._current is not None:
            self._current["snippet"] += data


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": "https://lite.duckduckgo.com/",
    "Origin": "https://lite.duckduckgo.com",
}

DDG_LITE_URL = "https://lite.duckduckgo.com/lite/"


def search_ddg(query: str, max_results: int = 10, delay: float = 0.0) -> list[dict]:
    """
    Fetch search results from DuckDuckGo Lite.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.
        delay: Optional delay in seconds before the request (rate limiting).

    Returns:
        List of dicts with keys: title, url, snippet.
    """
    if delay > 0:
        time.sleep(delay)

    body = urllib.parse.urlencode({"q": query}).encode("utf-8")
    req = urllib.request.Request(DDG_LITE_URL, data=body, headers=HEADERS, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            # Detect encoding from headers; default to utf-8
            content_type = resp.headers.get_content_charset("utf-8")
            raw_html = raw.decode(content_type, errors="replace")
    except Exception as exc:
        print(f"[search_ddg] Request failed: {exc}", file=sys.stderr)
        return []

    # Detect CAPTCHA / block page
    if "CAPTCHA" in raw_html or "captcha" in raw_html.lower():
        print(
            "[search_ddg] WARNING: DDG returned a CAPTCHA. Wait and retry.",
            file=sys.stderr,
        )
        return []

    parser = DDGLiteParser()
    parser.feed(raw_html)

    results = parser.results[:max_results]

    # Fallback: if DDG Lite HTML structure changed, try a simple link regex
    if not results:
        results = _fallback_regex_parse(raw_html, max_results)

    return results


def _fallback_regex_parse(html_text: str, max_results: int) -> list[dict]:
    """Regex fallback when the HTML structure is not recognised."""
    pattern = re.compile(
        r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL | re.IGNORECASE
    )
    results = []
    for m in pattern.finditer(html_text):
        url, raw_title = m.group(1), m.group(2)
        title = re.sub(r"<[^>]+>", "", raw_title).strip()
        if title and url.startswith("http") and "duckduckgo" not in url:
            results.append({"title": html.unescape(title), "url": url, "snippet": ""})
        if len(results) >= max_results:
            break
    return results


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def print_human(results: list[dict]) -> None:
    if not results:
        print("No results found.")
        return
    for i, r in enumerate(results, 1):
        print(f"[{i}] {r['title']}")
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
        description="Search DuckDuckGo Lite and return results (no API key required).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("query", help="Search query string")
    parser.add_argument(
        "--max", type=int, default=10, metavar="N",
        help="Maximum number of results (default: 10)"
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Output results as JSON array"
    )
    parser.add_argument(
        "--delay", type=float, default=0.0, metavar="SECONDS",
        help="Delay in seconds before request (for rate limiting)"
    )
    args = parser.parse_args()

    results = search_ddg(args.query, max_results=args.max, delay=args.delay)

    if args.json_output:
        print_json(results)
    else:
        print_human(results)


if __name__ == "__main__":
    main()
