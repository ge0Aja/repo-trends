import re
import time

import httpx

from .models import Candidate

USER_AGENT = "repo-trends/0.1 (+https://github.com/)"

_GH_RE = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")
_RESERVED_OWNERS = {
    "sponsors", "orgs", "users", "topics", "marketplace",
    "features", "settings", "about", "pricing", "readme",
    "trending", "collections", "events", "login", "join",
}


def _parse_github_url(url: str) -> tuple[str, str] | None:
    if not url:
        return None
    m = _GH_RE.search(url)
    if not m:
        return None
    owner, name = m.group(1), m.group(2)
    name = name.split("#")[0].split("?")[0].removesuffix(".git")
    if not name or owner.lower() in _RESERVED_OWNERS:
        return None
    return owner, name


def from_trending(client: httpx.Client, spans: tuple[str, ...] = ("daily",)) -> list[Candidate]:
    from bs4 import BeautifulSoup

    out: dict[tuple[str, str], Candidate] = {}
    for span in spans:
        r = client.get(
            f"https://github.com/trending?since={span}",
            headers={"User-Agent": USER_AGENT},
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for i, article in enumerate(soup.select("article.Box-row")):
            a = article.select_one("h2 a")
            if not a or not a.get("href"):
                continue
            parsed = _parse_github_url("github.com" + a["href"])
            if not parsed:
                continue
            owner, name = parsed
            key = (owner.lower(), name.lower())
            c = out.setdefault(key, Candidate(owner=owner, name=name))
            tag = f"trending:{span}"
            if tag not in c.sources:
                c.sources.append(tag)
            if c.trending_rank is None:
                c.trending_rank = i + 1
    return list(out.values())


def from_hn(client: httpx.Client, hours: int = 24) -> list[Candidate]:
    since = int(time.time() - hours * 3600)
    r = client.get(
        "https://hn.algolia.com/api/v1/search",
        params={
            "query": "github.com",
            "tags": "story",
            "numericFilters": f"created_at_i>{since}",
            "hitsPerPage": 100,
        },
        headers={"User-Agent": USER_AGENT},
    )
    r.raise_for_status()
    out: dict[tuple[str, str], Candidate] = {}
    for hit in r.json().get("hits", []):
        parsed = _parse_github_url(hit.get("url") or "")
        if not parsed:
            continue
        owner, name = parsed
        key = (owner.lower(), name.lower())
        c = out.setdefault(key, Candidate(owner=owner, name=name))
        if "hn" not in c.sources:
            c.sources.append("hn")
        points = hit.get("points") or 0
        if points > (c.hn_points or -1):
            c.hn_points = points
            c.hn_comments = hit.get("num_comments")
            c.hn_url = f"https://news.ycombinator.com/item?id={hit['objectID']}"
    return list(out.values())


def from_reddit(client: httpx.Client, subs: list[str]) -> list[Candidate]:
    out: dict[tuple[str, str], Candidate] = {}
    for sub in subs:
        try:
            r = client.get(
                f"https://www.reddit.com/r/{sub}/top.json",
                params={"t": "day", "limit": 50},
                headers={"User-Agent": USER_AGENT},
            )
            r.raise_for_status()
        except httpx.HTTPError:
            continue
        for child in r.json().get("data", {}).get("children", []):
            d = child.get("data", {})
            parsed = _parse_github_url(d.get("url", ""))
            if not parsed:
                continue
            owner, name = parsed
            key = (owner.lower(), name.lower())
            c = out.setdefault(key, Candidate(owner=owner, name=name))
            tag = f"reddit:{sub}"
            if tag not in c.sources:
                c.sources.append(tag)
            score = d.get("score") or 0
            if score > (c.reddit_score or -1):
                c.reddit_score = score
                c.reddit_url = f"https://reddit.com{d.get('permalink', '')}"
    return list(out.values())


def merge(batches: list[list[Candidate]]) -> list[Candidate]:
    merged: dict[tuple[str, str], Candidate] = {}
    for batch in batches:
        for c in batch:
            key = (c.owner.lower(), c.name.lower())
            existing = merged.get(key)
            if existing is None:
                merged[key] = c
                continue
            for s in c.sources:
                if s not in existing.sources:
                    existing.sources.append(s)
            if c.trending_rank is not None and (
                existing.trending_rank is None or c.trending_rank < existing.trending_rank
            ):
                existing.trending_rank = c.trending_rank
            if (c.hn_points or 0) > (existing.hn_points or 0):
                existing.hn_points = c.hn_points
                existing.hn_comments = c.hn_comments
                existing.hn_url = c.hn_url
            if (c.reddit_score or 0) > (existing.reddit_score or 0):
                existing.reddit_score = c.reddit_score
                existing.reddit_url = c.reddit_url
    return list(merged.values())


def rank_and_cap(candidates: list[Candidate], cap: int = 100) -> list[Candidate]:
    def score_key(c: Candidate) -> tuple[int, int, int, int]:
        distinct = len({s.split(":", 1)[0] for s in c.sources})
        trending = (1000 - c.trending_rank) if c.trending_rank else 0
        return (-distinct, -trending, -(c.hn_points or 0), -(c.reddit_score or 0))

    return sorted(candidates, key=score_key)[:cap]
