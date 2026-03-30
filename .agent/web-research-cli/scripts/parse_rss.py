#!/usr/bin/env python3
"""
parse_rss.py — Parse RSS 2.0 and Atom 1.0 feeds and output clean items.

Usage:
    python3 parse_rss.py https://hnrss.org/frontpage [--max N] [--json] [--filter KEYWORD]

    # Google News RSS (no API key)
    python3 parse_rss.py "https://news.google.com/rss/search?q=LLM+agents&hl=en-US&gl=US&ceid=US:en"

Output:
    Human-readable list or JSON array of {title, link, published, summary}.

Requires: python3 stdlib only (urllib, xml.etree.ElementTree)
"""

import argparse
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUEST_TIMEOUT = 15
MAX_FILE_BYTES = 1_048_576  # 1 MB

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
    ),
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
}

# Atom namespace
ATOM_NS = "http://www.w3.org/2005/Atom"
ATOM_TAG = f"{{{ATOM_NS}}}"

# Dublin Core namespace (used in some RSS feeds for better pubDate)
DC_NS = "http://purl.org/dc/elements/1.1/"
DC_TAG = f"{{{DC_NS}}}"

# Media namespace
MEDIA_NS = "http://search.yahoo.com/mrss/"


# ---------------------------------------------------------------------------
# Feed type detection
# ---------------------------------------------------------------------------

def detect_feed_type(root: ET.Element) -> str:
    """Return 'rss', 'atom', or 'unknown'."""
    tag = root.tag.lower()
    if "rss" in tag or root.tag == "rss":
        return "rss"
    if "feed" in tag or root.tag == f"{ATOM_TAG}feed" or root.tag == "feed":
        return "atom"
    return "unknown"


# ---------------------------------------------------------------------------
# RSS 2.0 parser
# ---------------------------------------------------------------------------

def _clean(text: str | None) -> str:
    if not text:
        return ""
    # Remove HTML tags from description/summary
    cleaned = re.sub(r"<[^>]+>", "", text)
    return html.unescape(cleaned).strip()


def parse_rss_feed(root: ET.Element) -> tuple[str, list[dict]]:
    """Parse RSS 2.0 feed. Returns (feed_title, items)."""
    channel = root.find("channel")
    if channel is None:
        channel = root  # Some feeds omit <channel>

    feed_title = _clean(channel.findtext("title"))

    items = []
    for item in channel.findall("item"):
        title = _clean(item.findtext("title"))
        link = (
            item.findtext("link")
            or item.findtext(f"{{{DC_NS}}}identifier")
            or ""
        ).strip()
        pub_date = (
            item.findtext("pubDate")
            or item.findtext(f"{DC_TAG}date")
            or ""
        ).strip()
        description = _clean(
            item.findtext("description")
            or item.findtext(f"{DC_TAG}description")
            or ""
        )
        # Some Google News feeds put a <source> inside the description
        guid = item.findtext("guid", "").strip()

        items.append({
            "title": title,
            "link": link or guid,
            "published": pub_date,
            "summary": description[:500],
        })

    return feed_title, items


# ---------------------------------------------------------------------------
# Atom 1.0 parser
# ---------------------------------------------------------------------------

def parse_atom_feed(root: ET.Element) -> tuple[str, list[dict]]:
    """Parse Atom 1.0 feed. Returns (feed_title, items)."""
    # Handle namespaced root
    ns = {"atom": ATOM_NS}

    def find_text(el: ET.Element, *paths: str) -> str:
        for path in paths:
            # Try with and without namespace
            text = el.findtext(path, namespaces=ns)
            if text:
                return text.strip()
            # Try stripped namespace
            text = el.findtext(path.replace("atom:", ""))
            if text:
                return text.strip()
        return ""

    feed_title = find_text(root, "atom:title", "title")

    items = []
    # Support both namespaced and unnamespaced entries
    entries = root.findall(f"{ATOM_TAG}entry") or root.findall("entry")
    for entry in entries:
        title = _clean(
            entry.findtext(f"{ATOM_TAG}title")
            or entry.findtext("title")
            or ""
        )

        # Link: prefer alternate HTML link
        link = ""
        for link_el in (
            entry.findall(f"{ATOM_TAG}link")
            + entry.findall("link")
        ):
            rel = link_el.get("rel", "alternate")
            href = link_el.get("href", "")
            if href and rel in ("alternate", ""):
                link = href
                break
        if not link:
            link = (
                entry.findtext(f"{ATOM_TAG}id")
                or entry.findtext("id")
                or ""
            ).strip()

        published = (
            entry.findtext(f"{ATOM_TAG}published")
            or entry.findtext("published")
            or entry.findtext(f"{ATOM_TAG}updated")
            or entry.findtext("updated")
            or ""
        ).strip()

        summary_el = (
            entry.find(f"{ATOM_TAG}summary")
            or entry.find("summary")
            or entry.find(f"{ATOM_TAG}content")
            or entry.find("content")
        )
        summary = _clean(
            (summary_el.text if summary_el is not None else "")
            or ""
        )

        items.append({
            "title": title,
            "link": link,
            "published": published,
            "summary": summary[:500],
        })

    return feed_title, items


# ---------------------------------------------------------------------------
# Fetch and parse
# ---------------------------------------------------------------------------

def fetch_feed(url: str) -> str:
    """Fetch a feed URL and return raw XML string."""
    req = urllib.request.Request(url, headers=BROWSER_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read(MAX_FILE_BYTES)
            charset = resp.headers.get_content_charset("utf-8")
            try:
                import gzip
                raw = gzip.decompress(raw)
            except Exception:
                pass
            return raw.decode(charset, errors="replace")
    except Exception as exc:
        print(f"[parse_rss] Fetch failed: {exc}", file=sys.stderr)
        return ""


def parse_feed(url: str) -> tuple[str, list[dict]]:
    """
    Fetch and parse an RSS or Atom feed.

    Returns:
        (feed_title, items) where items is a list of dicts.
    """
    raw = fetch_feed(url)
    if not raw:
        return "", []

    # Strip BOM if present
    raw = raw.lstrip("\ufeff")

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        print(f"[parse_rss] XML parse error: {exc}", file=sys.stderr)
        # Try to strip problematic XML declarations and retry
        cleaned = re.sub(r"<\?xml[^?]*\?>", "", raw, count=1).strip()
        try:
            root = ET.fromstring(cleaned)
        except ET.ParseError:
            print("[parse_rss] Could not parse feed XML.", file=sys.stderr)
            return "", []

    feed_type = detect_feed_type(root)

    if feed_type == "atom":
        return parse_atom_feed(root)
    else:
        # Default to RSS parser for both 'rss' and 'unknown'
        return parse_rss_feed(root)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def print_human(feed_title: str, items: list[dict]) -> None:
    if feed_title:
        print(f"Feed: {feed_title}")
        print("=" * 60)
    if not items:
        print("No items found.")
        return
    for i, item in enumerate(items, 1):
        print(f"[{i}] {item['title']}")
        if item["published"]:
            print(f"    Published: {item['published']}")
        print(f"    {item['link']}")
        if item["summary"]:
            print(f"    {item['summary'][:200]}")
        print()


def print_json_out(feed_title: str, items: list[dict]) -> None:
    out = {"feed_title": feed_title, "items": items}
    print(json.dumps(out, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch and parse RSS/Atom feeds. Supports Google News RSS.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("url", help="Feed URL (RSS 2.0 or Atom 1.0)")
    parser.add_argument(
        "--max", type=int, default=20, metavar="N",
        help="Maximum number of items to show (default: 20)"
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Output as JSON"
    )
    parser.add_argument(
        "--filter", default=None, dest="keyword",
        help="Only show items containing this keyword (case-insensitive)"
    )
    args = parser.parse_args()

    feed_title, items = parse_feed(args.url)

    # Apply keyword filter
    if args.keyword:
        kw = args.keyword.lower()
        items = [
            item for item in items
            if kw in item["title"].lower() or kw in item["summary"].lower()
        ]

    # Apply max limit
    items = items[: args.max]

    if args.json_output:
        print_json_out(feed_title, items)
    else:
        print_human(feed_title, items)


if __name__ == "__main__":
    main()
