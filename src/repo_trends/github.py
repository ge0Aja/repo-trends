import base64
import re

import httpx

from .models import Candidate, Repo

API = "https://api.github.com"


def client(token: str | None) -> httpx.Client:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "repo-trends/0.1",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(base_url=API, headers=headers, timeout=30.0)


def _contributors_count(gh: httpx.Client, owner: str, name: str) -> int | None:
    r = gh.get(
        f"/repos/{owner}/{name}/contributors",
        params={"per_page": 1, "anon": "true"},
    )
    if r.status_code != 200:
        return None
    link = r.headers.get("link")
    if not link:
        return len(r.json())
    m = re.search(r'<[^>]*[?&]page=(\d+)[^>]*>;\s*rel="last"', link)
    return int(m.group(1)) if m else None


def _readme_excerpt(gh: httpx.Client, owner: str, name: str, max_chars: int = 500) -> str | None:
    r = gh.get(f"/repos/{owner}/{name}/readme")
    if r.status_code != 200:
        return None
    try:
        md = base64.b64decode(r.json().get("content", "")).decode("utf-8", errors="replace")
    except Exception:
        return None
    md = re.sub(r"<!--.*?-->", "", md, flags=re.DOTALL)
    paragraphs: list[str] = []
    buf: list[str] = []
    skip_prefixes = ("#", "---", "===", "<", "![", "[![", "|", ">", "```", "- [!", "* [!")
    for line in md.splitlines():
        stripped = line.strip()
        if not stripped:
            if buf:
                paragraphs.append(" ".join(buf))
                buf = []
            continue
        if stripped.startswith(skip_prefixes):
            if buf:
                paragraphs.append(" ".join(buf))
                buf = []
            continue
        buf.append(stripped)
    if buf:
        paragraphs.append(" ".join(buf))
    for p in paragraphs:
        if len(p) < 60:
            continue
        p = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", p)
        p = re.sub(r"`([^`]+)`", r"\1", p)
        p = re.sub(r"\s+", " ", p).strip()
        if len(p) > max_chars:
            return p[:max_chars].rstrip() + "…"
        return p
    return None


def enrich(c: Candidate, date: str, gh: httpx.Client) -> Repo | None:
    r = gh.get(f"/repos/{c.owner}/{c.name}")
    if r.status_code != 200:
        return None
    d = r.json()
    owner = d["owner"]["login"]
    name = d["name"]
    return Repo(
        date=date,
        owner=owner,
        name=name,
        url=d["html_url"],
        description=d.get("description"),
        primary_language=d.get("language"),
        topics=list(d.get("topics") or []),
        stars=d.get("stargazers_count", 0),
        forks=d.get("forks_count", 0),
        contributors_count=_contributors_count(gh, owner, name),
        created_at=d.get("created_at", ""),
        pushed_at=d.get("pushed_at", ""),
        license=(d.get("license") or {}).get("spdx_id"),
        readme_excerpt=_readme_excerpt(gh, owner, name),
        sources=list(c.sources),
        hn_url=c.hn_url,
        hn_points=c.hn_points,
        hn_comments=c.hn_comments,
        reddit_url=c.reddit_url,
        reddit_score=c.reddit_score,
    )
