# repo-trends

Daily tracker of trending GitHub repositories across multiple sources.

Sources: GitHub Trending (daily + weekly), Hacker News (Algolia), Reddit
(configurable subreddits). Each repo is enriched with stars, contributors,
language, topics, description, and a README paragraph.

Daily theme / summary is handled separately by a Claude Code routine that
reads the dataset — not by this pipeline.

## Output

- `data/raw/YYYY-MM-DD.jsonl` — one row per repo, the mineable dataset.
- `logs/YYYY-MM-DD.md` — human-readable log: each repo with metadata and a
  paragraph.

## Fields per repo

`date`, `owner`, `name`, `url`, `description`, `primary_language`, `topics`,
`stars`, `forks`, `contributors_count`, `created_at`, `pushed_at`, `license`,
`readme_excerpt`, `sources`, `hn_url`, `hn_points`, `hn_comments`,
`reddit_url`, `reddit_score`.

`sources` is an array — a repo surfacing from multiple feeds (e.g.
`["trending:daily", "hn", "reddit:programming"]`) is itself a signal.

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install .
repo-trends --cap 100
```

Outputs land in `data/raw/` and `logs/` under the current directory.

## Environment variables

| Var            | Purpose                                                       |
| -------------- | ------------------------------------------------------------- |
| `GITHUB_TOKEN` | Read-only PAT. Raises GitHub API limit from 60/hr to 5000/hr. |

## CLI

```
repo-trends [--cap N] [--subreddits sub1 sub2 ...] [--out DIR]
```

## Scheduled runs

`.github/workflows/daily.yml` runs every day at 07:00 UTC and commits the
day's files back to the repo. No secrets required beyond the default
`GITHUB_TOKEN`.
