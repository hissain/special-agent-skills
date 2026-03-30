#!/usr/bin/env python3
"""
extract_text.py — Fetch and extract clean plain text from a URL or local HTML file.

Usage:
    python3 extract_text.py https://example.com/article
    python3 extract_text.py /path/to/local.html --local
    python3 extract_text.py https://example.com --json
    python3 extract_text.py https://example.com --jina       # Use Jina Reader (best quality)
    python3 extract_text.py https://example.com --max-chars 10000

Output:
    Cleaned plain text, or JSON with {url, title, text, char_count}.

Requires: python3 stdlib only (urllib, html.parser)
Fallback: Jina Reader (r.jina.ai) — requires internet access
"""

import argparse
import html
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MAX_CHARS = 50_000
REQUEST_TIMEOUT = 15
MAX_FILE_BYTES = 524_288  # 512 KB

# Tags whose content we skip entirely
SKIP_TAGS = {
    "script", "style", "noscript", "iframe", "svg", "canvas",
    "head", "meta", "link", "base",
}
# Tags that are boilerplate containers — we skip their content
BOILERPLATE_TAGS = {"nav", "header", "footer", "aside", "form", "button", "dialog"}

# Tags that contribute to readable text
BLOCK_TAGS = {
    "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "li", "dt", "dd", "blockquote", "pre", "code",
    "article", "main", "section", "div", "td", "th", "caption",
    "figcaption", "summary", "details",
}

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip",
}


# ---------------------------------------------------------------------------
# HTML text extractor
# ---------------------------------------------------------------------------

class TextExtractor(HTMLParser):
    """
    Extracts readable text from HTML.
    Skips scripts, styles, nav, headers, footers, and other boilerplate.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip_depth: int = 0      # depth inside a skipped tag tree
        self._boiler_depth: int = 0    # depth inside boilerplate tag tree
        self.parts: list[str] = []
        self.title: str = ""
        self._in_title: bool = False
        self._last_was_block: bool = False
        self._tag_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list):
        self._tag_stack.append(tag)
        if tag == "title":
            self._in_title = True
            return
        if tag in SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth > 0:
            return
        if tag in BOILERPLATE_TAGS:
            self._boiler_depth += 1
            return
        if tag in BLOCK_TAGS and self._boiler_depth == 0:
            self._last_was_block = True

    def handle_endtag(self, tag: str):
        if self._tag_stack:
            self._tag_stack.pop()
        if tag == "title":
            self._in_title = False
            return
        if tag in SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag in BOILERPLATE_TAGS:
            self._boiler_depth = max(0, self._boiler_depth - 1)
            return
        if tag in BLOCK_TAGS and self._boiler_depth == 0:
            self._flush_newline()

    def _flush_newline(self):
        if self.parts and self.parts[-1] != "\n":
            self.parts.append("\n")
        self._last_was_block = False

    def handle_data(self, data: str):
        if self._in_title:
            self.title += data
            return
        if self._skip_depth > 0 or self._boiler_depth > 0:
            return
        text = data.replace("\r\n", "\n").replace("\r", "\n")
        # Collapse interior whitespace but keep newlines
        lines = [" ".join(line.split()) for line in text.split("\n")]
        cleaned = "\n".join(lines)
        if cleaned.strip():
            if self._last_was_block and self.parts and self.parts[-1] != "\n":
                self.parts.append("\n")
                self._last_was_block = False
            self.parts.append(cleaned)

    def get_text(self) -> str:
        raw = "".join(self.parts)
        # Collapse 3+ consecutive newlines to 2
        return re.sub(r"\n{3,}", "\n\n", raw).strip()


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------

def fetch_url(url: str) -> str:
    """Fetch a URL using urllib and return decoded HTML string."""
    req = urllib.request.Request(url, headers=BROWSER_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read(MAX_FILE_BYTES)
            charset = resp.headers.get_content_charset("utf-8")
            # Handle gzip transparently
            try:
                import gzip
                raw = gzip.decompress(raw)
            except Exception:
                pass
            return raw.decode(charset, errors="replace")
    except Exception as exc:
        print(f"[extract_text] Fetch failed: {exc}", file=sys.stderr)
        return ""


def fetch_jina(url: str) -> str:
    """
    Use Jina Reader (r.jina.ai) to convert a URL to clean Markdown text.
    Great for JS-heavy pages and paywalled articles.
    """
    jina_url = f"https://r.jina.ai/{url}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
        ),
        "Accept": "text/markdown,text/plain,*/*",
    }
    req = urllib.request.Request(jina_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read(MAX_FILE_BYTES)
            charset = resp.headers.get_content_charset("utf-8")
            return raw.decode(charset, errors="replace")
    except Exception as exc:
        print(f"[extract_text] Jina Reader failed: {exc}", file=sys.stderr)
        return ""


def read_local_file(path: str) -> str:
    """Read a local HTML file."""
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        print(f"[extract_text] Cannot read file: {exc}", file=sys.stderr)
        return ""


def extract(html_text: str) -> tuple[str, str]:
    """
    Extract title and body text from raw HTML.
    Returns (title, body_text).
    """
    parser = TextExtractor()
    parser.feed(html_text)
    return parser.title.strip(), parser.get_text()


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def print_human(title: str, text: str, max_chars: int) -> None:
    if title:
        print(f"=== {title} ===\n")
    print(text[:max_chars])
    if len(text) > max_chars:
        print(f"\n... [truncated — {len(text) - max_chars} more chars] ...")


def print_json_out(url: str, title: str, text: str, max_chars: int) -> None:
    out = {
        "url": url,
        "title": title,
        "text": text[:max_chars],
        "char_count": len(text),
        "truncated": len(text) > max_chars,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch a URL or local HTML file and output clean plain text.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "source",
        help="URL to fetch OR local file path (use --local for files)"
    )
    parser.add_argument(
        "--local", action="store_true",
        help="Treat SOURCE as a local file path, not a URL"
    )
    parser.add_argument(
        "--jina", action="store_true",
        help="Use Jina Reader (r.jina.ai) for better extraction of JS-heavy pages"
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Output as JSON with metadata"
    )
    parser.add_argument(
        "--max-chars", type=int, default=DEFAULT_MAX_CHARS, dest="max_chars",
        metavar="N",
        help=f"Maximum characters to output (default: {DEFAULT_MAX_CHARS})"
    )
    args = parser.parse_args()

    # Determine source label for JSON output
    url_label = args.source if not args.local else f"file://{args.source}"

    # Fetch content
    if args.jina and not args.local:
        raw = fetch_jina(args.source)
        title = ""  # Jina returns Markdown — no HTML title parsing needed
        body = raw
    elif args.local:
        raw = read_local_file(args.source)
        if not raw:
            sys.exit(1)
        title, body = extract(raw)
    else:
        raw = fetch_url(args.source)
        if not raw:
            # Try Jina Reader as automatic fallback
            print(
                "[extract_text] Primary fetch returned empty. Trying Jina Reader...",
                file=sys.stderr,
            )
            raw = fetch_jina(args.source)
            title = ""
            body = raw
        else:
            title, body = extract(raw)

    if not body.strip():
        print("[extract_text] WARNING: No readable text extracted.", file=sys.stderr)

    if args.json_output:
        print_json_out(url_label, title, body, args.max_chars)
    else:
        print_human(title, body, args.max_chars)


if __name__ == "__main__":
    main()
