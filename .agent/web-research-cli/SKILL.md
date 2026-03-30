---
name: web-research-cli
description: >
  Enables any LLM agent to perform internet research, summarise findings, and act on
  web-sourced information using ONLY curl, wget, and python3 (stdlib). No browser, no MCP,
  no API keys required for core functionality. Use this skill whenever the task requires
  fetching live information from the web and the agent has no browser or MCP tool access.
  Covers: web search (DuckDuckGo Lite / Brave API), RSS/news feeds, REST APIs (Wikipedia,
  arXiv, GitHub), and general webpage scraping/text extraction.
license: MIT
compatibility: "Requires curl and python3 (3.8+, stdlib only). Optional: Brave Search API key."
metadata:
  version: "1.0"
  author: "special-agent-skills"
  tags: ["research", "curl", "no-browser", "enterprise", "air-gapped"]
---

# Web Research CLI Skill

## Purpose

This skill gives LLM agents running in environments **without a browser, MCP, or dedicated
web-search tool** the ability to:

1. Search the web for recent information
2. Read and parse web pages as clean text
3. Consume RSS / news feeds
4. Query structured REST APIs (Wikipedia, arXiv, GitHub)
5. Summarise and act on the retrieved content

All operations are performed entirely through `curl` shell commands and `python3` scripts
that rely exclusively on the **standard library** (no `pip install` required).

---

## Quick-Reference Routing Table

| Task | Tool to use | Reference doc |
|------|-------------|---------------|
| Search the web | `scripts/search_ddg.py` | `references/search.md` |
| Fetch + read a webpage | `scripts/extract_text.py` | `references/scraping.md` |
| Read RSS / news feed | `scripts/parse_rss.py` | `references/rss.md` |
| Wikipedia article | direct `curl` + `jq` / script | `references/apis.md` |
| arXiv preprints | direct `curl` (Atom XML) | `references/apis.md` |
| GitHub repos/issues | direct `curl` + JSON | `references/apis.md` |
| Brave Search API | `scripts/search_brave.py` | `references/search.md` |

---

## Workflow: Research → Summarise → Act

Follow this pattern for any research task:

### Step 1 — Choose a retrieval method

- **Known URL?** → use `extract_text.py` directly.
- **Unknown URL, need to find sources?** → use `search_ddg.py` first.
- **Topic has a structured data source** (Wikipedia / arXiv / GitHub)? → prefer the REST
  API over scraping. See `references/apis.md`.
- **Monitoring ongoing news?** → use `parse_rss.py`. See `references/rss.md`.

### Step 2 — Retrieve content

Run the appropriate script. All scripts support `--json` for machine-readable output and
can be piped together.

```bash
# Example: search then extract top result
python3 scripts/search_ddg.py "python asyncio tutorial" --max 3 --json | \
  python3 -c "import sys,json; results=json.load(sys.stdin); print(results[0]['url'])" | \
  xargs -I{} python3 scripts/extract_text.py {}
```

### Step 3 — Summarise

Feed the cleaned text back to the LLM. Truncate to a reasonable chunk (≤ 8 000 tokens)
before sending. If the page is very long, chunk it and summarise iteratively.

### Step 4 — Act

Use the summarised content to answer the user's question, generate a report, update a
file, make a decision, or trigger the next step in a pipeline.

---

## Environment Check

Before using this skill, confirm the environment has the required tools:

```bash
# Check curl
curl --version | head -1

# Check python3
python3 --version

# Optional: check jq (for JSON pretty-printing)
jq --version
```

---

## Gotchas & Constraints

- **Rate limits**: DuckDuckGo Lite will temporarily block repeated rapid requests.
  Add `--delay 2` or use Brave Search API with a key for automated pipelines.
- **JavaScript-rendered pages**: `curl` cannot execute JS. Use Jina Reader
  (`https://r.jina.ai/<url>`) as a zero-dependency fallback — it returns clean text.
- **HTTPS only**: Always prefer `https://` URLs. Add `-L` to follow redirects.
- **Large pages**: Cap fetched content at 500 KB using `curl --max-filesize 524288`.
- **Paywall / 403 errors**: Try the Jina Reader fallback. See `references/scraping.md`.
- **Encoding**: Always decode responses as UTF-8. The scripts handle this automatically.

---

## Loading Reference Docs

Load reference docs **on demand** — only when you need the detailed patterns for that
specific source type. Do not load all references at once.

- `references/search.md` — search engine strategies, query crafting, result parsing
- `references/scraping.md` — HTML-to-text pipeline, Jina Reader, anti-bot headers
- `references/rss.md` — RSS/Atom parsing, Google News RSS, feed discovery
- `references/apis.md` — Wikipedia, arXiv, GitHub REST API curl patterns
