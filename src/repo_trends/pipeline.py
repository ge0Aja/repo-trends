import argparse
import datetime as dt
import json
import os
import pathlib
import sys

import httpx

from . import github, render, sources

DEFAULT_SUBS = [
    "programming",
    "opensource",
    "selfhosted",
    "MachineLearning",
    "LocalLLaMA",
    "golang",
    "rust",
    "Python",
]


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def run(out_dir: pathlib.Path, cap: int, subs: list[str]) -> int:
    today = dt.date.today().isoformat()
    raw_path = out_dir / "data" / "raw" / f"{today}.jsonl"
    md_path = out_dir / "logs" / f"{today}.md"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=30.0, follow_redirects=True) as web:
        batches: list[list] = []
        for label, fn in (
            ("trending", lambda: sources.from_trending(web, ("daily", "weekly"))),
            ("hn", lambda: sources.from_hn(web)),
            ("reddit", lambda: sources.from_reddit(web, subs)),
        ):
            try:
                found = fn()
                log(f"[discover] {label}: {len(found)}")
                batches.append(found)
            except Exception as e:
                log(f"[discover] {label} failed: {e}")

    candidates = sources.rank_and_cap(sources.merge(batches), cap=cap)
    log(f"[discover] {len(candidates)} after dedupe and cap")

    repos = []
    with github.client(os.getenv("a")) as gh:
        for c in candidates:
            try:
                r = github.enrich(c, today, gh)
                if r:
                    repos.append(r)
            except Exception as e:
                log(f"[enrich] {c.owner}/{c.name} failed: {e}")
    log(f"[enrich] {len(repos)} enriched")

    with raw_path.open("w") as f:
        for r in repos:
            f.write(json.dumps(r.to_dict()) + "\n")
    log(f"[write] {raw_path}")

    md_path.write_text(render.render_markdown(today, repos))
    log(f"[write] {md_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser("repo-trends")
    p.add_argument("--out", type=pathlib.Path, default=pathlib.Path.cwd())
    p.add_argument("--cap", type=int, default=100)
    p.add_argument("--subreddits", nargs="*", default=DEFAULT_SUBS)
    a = p.parse_args(argv)
    return run(a.out, a.cap, a.subreddits)


if __name__ == "__main__":
    sys.exit(main())
