# Webpage Scraping & Text Extraction Reference

## 1. The Extraction Pipeline

```
URL
 └─► curl fetch (raw HTML / redirect chain)
       └─► strip tags, boilerplate, nav, footer (extract_text.py)
             └─► clean UTF-8 text (≤ 50 000 chars)
                   └─► LLM summarisation
```

---

## 2. Using extract_text.py

```bash
# Fetch and extract a URL
python3 scripts/extract_text.py https://en.wikipedia.org/wiki/Transformer_(deep_learning)

# Extract a local HTML file
python3 scripts/extract_text.py /tmp/page.html --local

# JSON output with metadata
python3 scripts/extract_text.py https://example.com/article --json

# Limit output length (default 50 000 chars)
python3 scripts/extract_text.py https://example.com --max-chars 10000

# Try Jina Reader first (better quality, requires internet)
python3 scripts/extract_text.py https://example.com --jina
```

---

## 3. Jina Reader — Best Fallback for Difficult Pages

[Jina AI Reader](https://jina.ai/reader/) converts any URL to clean Markdown with a
single `curl` call. **No API key needed** (rate-limited free tier).

```bash
# Basic usage — replace URL with target
curl -s "https://r.jina.ai/https://example.com/article" | head -200

# With a user-agent header (improves success rate)
curl -s \
  -H "User-Agent: Mozilla/5.0" \
  "https://r.jina.ai/https://techcrunch.com/2025/03/15/article-slug/"

# Save to file
curl -s "https://r.jina.ai/https://example.com" -o /tmp/article.md
```

**When to use Jina Reader:**
- JavaScript-heavy pages (React, Vue SPAs) that return empty content from plain curl
- Paywalled articles (sometimes works via cached/google-cached URLs)
- When `extract_text.py` returns less than 200 characters

---

## 4. Raw curl Fetch

```bash
# Standard fetch with browser-like headers
curl -s -L \
  --max-filesize 524288 \
  --max-time 15 \
  -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0" \
  -H "Accept: text/html,application/xhtml+xml" \
  -H "Accept-Language: en-US,en;q=0.9" \
  -H "Accept-Encoding: gzip" \
  --compressed \
  "https://example.com/page" \
  -o /tmp/page.html

# Pass to extractor
python3 scripts/extract_text.py /tmp/page.html --local
```

**Flags explained:**
| Flag | Purpose |
|------|---------|
| `-L` | Follow redirects |
| `--max-filesize 524288` | Cap at 512 KB — prevents downloading huge files |
| `--max-time 15` | Abort after 15 seconds |
| `--compressed` | Handle gzip responses |
| `-s` | Silent mode (no progress bar) |

---

## 5. Anti-Bot & 403 Handling

When curl returns a 403 or Cloudflare challenge page:

```bash
# Strategy 1: Try Jina Reader
curl -s "https://r.jina.ai/PROBLEM_URL"

# Strategy 2: Google Cache
curl -s "https://webcache.googleusercontent.com/search?q=cache:PROBLEM_URL" | \
  python3 scripts/extract_text.py /dev/stdin --local

# Strategy 3: Archive.org Wayback Machine (latest snapshot)
ENCODED_URL=$(python3 -c "import urllib.parse; print(urllib.parse.quote('PROBLEM_URL'))")
curl -s "http://archive.org/wayback/available?url=${ENCODED_URL}" | \
  python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('archived_snapshots',{}).get('closest',{}).get('url','NOT FOUND'))"
```

---

## 6. Handling Different Content Types

### PDFs
```bash
# Download and extract text (requires pdftotext / python3 with pdfminer)
curl -sL "https://example.com/paper.pdf" -o /tmp/doc.pdf

# With python3 stdlib only — limited but functional
python3 -c "
import subprocess, sys
result = subprocess.run(['python3', '-m', 'pydoc', '/tmp/doc.pdf'], 
                        capture_output=True, text=True)
print(result.stdout)
"

# Better: use pdftotext if available
pdftotext /tmp/doc.pdf -
```

### JSON APIs
```bash
# Always pretty-print JSON
curl -s "https://api.example.com/data" | python3 -m json.tool | head -100
```

### Plain text / Markdown
```bash
curl -sL "https://raw.githubusercontent.com/user/repo/main/README.md"
```

---

## 7. Text Cleaning Rules (what extract_text.py does)

The script removes:
- `<script>`, `<style>`, `<noscript>` tags and their contents
- `<nav>`, `<header>`, `<footer>`, `<aside>` elements (boilerplate)
- HTML comments
- Excess whitespace (collapses to single newlines)
- Cookie consent banners (heuristic: removes short `<div>` blocks with "cookie" in text)

It preserves:
- `<article>`, `<main>`, `<section>`, `<p>`, `<h1>`–`<h6>`, `<li>`, `<pre>`, `<code>`
- Link text (href stripped, anchor text kept)
- Table content (rendered as plain text rows)
