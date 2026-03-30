# Web Search Reference

## 1. DuckDuckGo Lite (No API Key)

DuckDuckGo's `/lite` endpoint returns plain HTML with minimal JavaScript — ideal for
scraping from CLI environments.

### Using the script

```bash
# Basic search — prints titles, URLs, snippets
python3 scripts/search_ddg.py "latest transformer architecture papers" --max 5

# JSON output for piping
python3 scripts/search_ddg.py "rust async runtime comparison" --max 10 --json

# With delay between retries (recommended for automated use)
python3 scripts/search_ddg.py "site:github.com langchain" --max 5 --delay 2
```

### Raw curl (manual)

```bash
# POST to DDG Lite
curl -s -L \
  -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0" \
  -H "Accept: text/html" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "q=YOUR QUERY HERE" \
  "https://lite.duckduckgo.com/lite/" > /tmp/ddg_results.html

# Then parse with extract_text.py
python3 scripts/extract_text.py /tmp/ddg_results.html --local
```

### DDG search operators

| Operator | Effect |
|----------|--------|
| `site:example.com` | Restrict to domain |
| `filetype:pdf` | Specific file type |
| `"exact phrase"` | Exact match |
| `-word` | Exclude word |
| `intitle:keyword` | Keyword in page title |
| `after:2024-01-01` | Filter by date |

---

## 2. Brave Search API (Recommended for Automated Pipelines)

Requires a free API key from https://brave.com/search/api/. Free tier: 2,000 queries/month.

### Setup

```bash
export BRAVE_API_KEY="your_key_here"
```

### Using the script

```bash
python3 scripts/search_brave.py "quantum computing 2025" --max 5 --json
```

### Raw curl

```bash
curl -s \
  -H "Accept: application/json" \
  -H "Accept-Encoding: gzip" \
  -H "X-Subscription-Token: ${BRAVE_API_KEY}" \
  "https://api.search.brave.com/res/v1/web/search?q=YOUR+QUERY&count=10&freshness=pw" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
for r in data.get('web', {}).get('results', []):
    print(r['title'])
    print(r['url'])
    print(r.get('description', ''))
    print('---')
"
```

### Brave API parameters

| Parameter | Values | Notes |
|-----------|--------|-------|
| `count` | 1–20 | Results per page |
| `freshness` | `pd` (day), `pw` (week), `pm` (month), `py` (year) | Date filter |
| `search_lang` | `en`, `fr`, etc. | Result language |
| `country` | `US`, `GB`, etc. | Country filter |
| `safesearch` | `off`, `moderate`, `strict` | Content filter |

---

## 3. Query Crafting Tips

- **Be specific**: `"python asyncio gather timeout fix"` beats `"python async"`.
- **Use site: for known sources**: `site:arxiv.org transformer 2024`.
- **Date-limit for freshness**: Add `after:2024-01-01` or use Brave's `freshness` param.
- **Retry on failure**: DDG may return a CAPTCHA page — detect it by checking if the
  response HTML contains the word "CAPTCHA" and wait 2–3 seconds before retrying.
- **Parse the top 3–5 results**, not just #1 — the first result is not always the best.

---

## 4. Parsing Search Results

After `search_ddg.py --json` you get:

```json
[
  {
    "title": "Page Title",
    "url": "https://example.com/page",
    "snippet": "Short description from DDG..."
  }
]
```

Pass the URL to `extract_text.py` to get the full content:

```bash
python3 scripts/search_ddg.py "topic" --max 3 --json | \
  python3 -c "
import sys, json, subprocess
results = json.load(sys.stdin)
for r in results[:2]:
    print(f\"=== {r['title']} ===\")
    out = subprocess.run(['python3', 'scripts/extract_text.py', r['url']], 
                         capture_output=True, text=True)
    print(out.stdout[:3000])
    print()
"
```
