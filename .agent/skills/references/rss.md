# RSS / Atom Feed Reference

## 1. Using parse_rss.py

```bash
# Parse any RSS or Atom feed — prints titles, links, pub dates, summaries
python3 scripts/parse_rss.py https://feeds.feedburner.com/TechCrunch

# JSON output
python3 scripts/parse_rss.py https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml --json

# Limit number of items
python3 scripts/parse_rss.py https://hnrss.org/frontpage --max 10

# Filter items containing a keyword
python3 scripts/parse_rss.py https://hnrss.org/frontpage --filter "LLM" --max 20
```

---

## 2. Google News RSS (No API Key)

Google News provides free RSS feeds for any search topic. These are among the most
reliable no-auth news sources available.

### Pattern
```
https://news.google.com/rss/search?q=QUERY&hl=en-US&gl=US&ceid=US:en
```

### Examples

```bash
# Latest AI news
python3 scripts/parse_rss.py \
  "https://news.google.com/rss/search?q=artificial+intelligence&hl=en-US&gl=US&ceid=US:en" \
  --max 10 --json

# News about a company
python3 scripts/parse_rss.py \
  "https://news.google.com/rss/search?q=OpenAI+site:techcrunch.com&hl=en-US" \
  --max 5

# Recent news (last 7 days) using `when:7d` operator
python3 scripts/parse_rss.py \
  "https://news.google.com/rss/search?q=quantum+computing+when:7d&hl=en-US&gl=US&ceid=US:en" \
  --max 10
```

---

## 3. Curated Feed List by Domain

| Topic | Feed URL |
|-------|----------|
| Hacker News front page | `https://hnrss.org/frontpage` |
| Hacker News newest | `https://hnrss.org/newest` |
| HN: AI/ML posts | `https://hnrss.org/newest?q=machine+learning` |
| arXiv cs.AI | `https://rss.arxiv.org/rss/cs.AI` |
| arXiv cs.LG | `https://rss.arxiv.org/rss/cs.LG` |
| arXiv cs.CL | `https://rss.arxiv.org/rss/cs.CL` |
| GitHub trending | *(no official RSS — use GitHub API, see apis.md)* |
| NYT Technology | `https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml` |
| BBC Tech | `https://feeds.bbci.co.uk/news/technology/rss.xml` |
| The Verge | `https://www.theverge.com/rss/index.xml` |
| MIT Tech Review | `https://www.technologyreview.com/feed/` |
| VentureBeat AI | `https://venturebeat.com/category/ai/feed/` |

---

## 4. Feed Discovery

If you have a website URL but not its feed URL:

```bash
# Check common feed paths
BASE_URL="https://example.com"
for path in feed rss atom feeds feed.xml rss.xml atom.xml index.xml; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/${path}")
    if [ "$STATUS" = "200" ]; then
        echo "Found: ${BASE_URL}/${path}"
    fi
done
```

Or use the HTML `<link>` tag discovery:

```bash
curl -sL "https://example.com" | \
  python3 -c "
import sys, re
html = sys.stdin.read()
# Find RSS/Atom link tags
feeds = re.findall(r'<link[^>]+type=[\"\'](application/rss\+xml|application/atom\+xml)[\"\']+[^>]*href=[\"\'](.*?)[\"\']+', html)
for _, url in feeds:
    print(url)
"
```

---

## 5. Raw curl for RSS

```bash
# Fetch and display raw XML
curl -sL "https://hnrss.org/frontpage" | \
  python3 -c "
import sys, xml.etree.ElementTree as ET
tree = ET.parse(sys.stdin)
root = tree.getroot()
for item in root.findall('.//item')[:5]:
    title = item.findtext('title', '')
    link  = item.findtext('link', '')
    desc  = item.findtext('description', '')[:200]
    print(f'TITLE: {title}')
    print(f'LINK:  {link}')
    print(f'DESC:  {desc}')
    print('---')
"
```

---

## 6. Monitoring Workflow (Scheduled Research)

Use this pattern to stay up-to-date on a topic without a browser:

```bash
#!/usr/bin/env python3
# monitor_topic.py — run periodically from cron or task scheduler

import subprocess, json, datetime

TOPIC = "large language model fine-tuning"
FEED  = f"https://news.google.com/rss/search?q={TOPIC.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"
TODAY = datetime.date.today().isoformat()

result = subprocess.run(
    ["python3", "scripts/parse_rss.py", FEED, "--max", "5", "--json"],
    capture_output=True, text=True
)
items = json.loads(result.stdout)
new_items = [i for i in items if TODAY in i.get("published", "")]
for item in new_items:
    print(item["title"], item["link"])
```
