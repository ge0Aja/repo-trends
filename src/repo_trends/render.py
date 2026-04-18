from .models import Repo


def render_markdown(date: str, repos: list[Repo]) -> str:
    lines: list[str] = [f"# Repo trends — {date}", ""]
    lines.append(f"_{len(repos)} repos across GitHub Trending, Hacker News, and Reddit._")
    lines.append("")
    lines += ["## Repositories", ""]
    for r in sorted(repos, key=lambda x: x.stars, reverse=True):
        lines.append(f"### [{r.owner}/{r.name}]({r.url})")
        meta: list[str] = []
        if r.primary_language:
            meta.append(f"`{r.primary_language}`")
        meta.append(f"⭐ {r.stars:,}")
        if r.contributors_count is not None:
            meta.append(f"👥 {r.contributors_count}")
        if r.topics:
            meta.append(" ".join(f"`#{t}`" for t in r.topics[:5]))
        meta.append(f"_sources: {', '.join(r.sources)}_")
        lines.append(" · ".join(meta))
        lines.append("")
        desc = (r.description or "").strip()
        excerpt = (r.readme_excerpt or "").strip()
        paragraph = excerpt if len(excerpt) > len(desc) else desc
        if paragraph:
            lines += [paragraph, ""]
        extras: list[str] = []
        if r.hn_url:
            hn = f"[HN]({r.hn_url})"
            if r.hn_points is not None:
                hn += f" · {r.hn_points} pts · {r.hn_comments or 0} comments"
            extras.append(hn)
        if r.reddit_url:
            rd = f"[Reddit]({r.reddit_url})"
            if r.reddit_score is not None:
                rd += f" · {r.reddit_score} pts"
            extras.append(rd)
        if extras:
            lines += [" · ".join(extras), ""]
    return "\n".join(lines).rstrip() + "\n"
