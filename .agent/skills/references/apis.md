# REST API Reference (curl-based, No Browser Required)

All APIs below are **free and require no authentication** unless marked with 🔑.

---

## 1. Wikipedia REST API

### Search Wikipedia

```bash
# Search for articles
curl -s "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=QUERY&format=json&srlimit=5" | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
for r in data['query']['search']:
    print(r['title'], '—', r['snippet'][:120])
"
```

### Get Article Summary (OpenSearch / REST Summary API)

```bash
# Clean article summary — best for quick facts
TITLE="Transformer_(machine_learning_model)"
curl -s "https://en.wikipedia.org/api/rest_v1/page/summary/${TITLE}" | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d['title'])
print(d['extract'])
"
```

### Get Full Article Text

```bash
# Plain text extract (up to full article)
TITLE="Transformer_(machine_learning_model)"
curl -s "https://en.wikipedia.org/w/api.php?action=query&titles=${TITLE}&prop=extracts&explaintext=true&format=json" | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
pages = data['query']['pages']
for pid, page in pages.items():
    print(page.get('extract', '')[:5000])
"
```

### Search & Summarize (combined pipeline)

```bash
QUERY="attention mechanism deep learning"
TITLE=$(curl -s "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=${QUERY// /+}&format=json&srlimit=1" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d['query']['search'][0]['title'].replace(' ','_'))")

echo "Article: $TITLE"
curl -s "https://en.wikipedia.org/api/rest_v1/page/summary/${TITLE}" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d['extract'])"
```

---

## 2. arXiv API (Preprints)

Returns Atom XML. No auth required.

```bash
# Search arXiv
QUERY="vision+transformer+2024"
curl -s "https://export.arxiv.org/api/query?search_query=all:${QUERY}&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending" | \
  python3 -c "
import sys, xml.etree.ElementTree as ET
ns = {'atom': 'http://www.w3.org/2005/Atom'}
tree = ET.parse(sys.stdin)
root = tree.getroot()
for entry in root.findall('atom:entry', ns):
    title   = entry.findtext('atom:title', '', ns).strip()
    link    = entry.find('atom:id', ns).text
    summary = entry.findtext('atom:summary', '', ns).strip()[:300]
    authors = [a.findtext('atom:name', '', ns) for a in entry.findall('atom:author', ns)]
    print(f'TITLE:   {title}')
    print(f'AUTHORS: {\", \".join(authors[:3])}')
    print(f'LINK:    {link}')
    print(f'SUMMARY: {summary}')
    print('---')
"
```

### arXiv Search Operators

| Operator | Example | Description |
|----------|---------|-------------|
| `all:` | `all:transformer` | Search all fields |
| `ti:` | `ti:attention` | Title only |
| `au:` | `au:lecun` | Author name |
| `abs:` | `abs:diffusion` | Abstract |
| `cat:` | `cat:cs.LG` | Category |

### Key Categories

| Code | Topic |
|------|-------|
| `cs.AI` | Artificial Intelligence |
| `cs.LG` | Machine Learning |
| `cs.CL` | Computation & Language (NLP) |
| `cs.CV` | Computer Vision |
| `cs.RO` | Robotics |
| `stat.ML` | Statistics / ML |
| `quant-ph` | Quantum Physics |

### Get Latest Papers in a Category

```bash
curl -s "https://rss.arxiv.org/rss/cs.LG" | \
  python3 -c "
import sys, xml.etree.ElementTree as ET
tree = ET.parse(sys.stdin)
root = tree.getroot()
for item in root.findall('.//item')[:5]:
    print(item.findtext('title', '').strip())
    print(item.findtext('link', ''))
    print()
"
```

---

## 3. GitHub REST API

### Search Repositories

```bash
# Search repos — no auth (60 req/hr unauthenticated)
QUERY="llm+agent+framework"
curl -s \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/search/repositories?q=${QUERY}&sort=stars&order=desc&per_page=5" | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
for r in data['items']:
    print(f\"{r['full_name']} ⭐ {r['stargazers_count']}\")
    print(f\"  {r['description']}\")
    print(f\"  {r['html_url']}\")
    print()
"
```

### 🔑 Authenticated (higher rate limit: 5000 req/hr)

```bash
export GITHUB_TOKEN="ghp_your_token_here"
curl -s \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/search/repositories?q=langchain&sort=stars&per_page=5"
```

### Get README of a Repo

```bash
OWNER="langchain-ai"
REPO="langchain"
curl -sL "https://raw.githubusercontent.com/${OWNER}/${REPO}/main/README.md" | head -100
```

### List Recent Releases

```bash
curl -s \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/openai/openai-python/releases?per_page=5" | \
  python3 -c "
import sys, json
releases = json.load(sys.stdin)
for r in releases:
    print(r['tag_name'], r['published_at'], r['name'])
"
```

### Search Issues / PRs

```bash
QUERY="is:issue+is:open+label:bug+repo:openai/openai-python"
curl -s \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/search/issues?q=${QUERY}&per_page=5" | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
for i in data['items']:
    print(f\"#{i['number']} {i['title']}\")
    print(f\"  {i['html_url']}\")
"
```

---

## 4. Other Useful No-Auth APIs

### Open-Meteo (Weather — no key)

```bash
# Current weather for a location (lat/lon)
curl -s "https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&current_weather=true" | \
  python3 -m json.tool | grep -A5 "current_weather"
```

### JSONPlaceholder (Mock/Test REST API)

```bash
curl -s "https://jsonplaceholder.typicode.com/posts?_limit=3" | python3 -m json.tool
```

### REST Countries

```bash
curl -s "https://restcountries.com/v3.1/name/germany" | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
c = data[0]
print(c['name']['common'], c['capital'], c['population'])
"
```

### Exchange Rates (open.er-api.com — free tier)

```bash
curl -s "https://open.er-api.com/v6/latest/USD" | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
for currency in ['EUR', 'GBP', 'JPY', 'BDT']:
    print(f\"1 USD = {data['rates'].get(currency, 'N/A')} {currency}\")
"
```
