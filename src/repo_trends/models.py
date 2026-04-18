from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class Candidate:
    owner: str
    name: str
    sources: list[str] = field(default_factory=list)
    trending_rank: Optional[int] = None
    hn_url: Optional[str] = None
    hn_points: Optional[int] = None
    hn_comments: Optional[int] = None
    reddit_url: Optional[str] = None
    reddit_score: Optional[int] = None

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"


@dataclass
class Repo:
    date: str
    owner: str
    name: str
    url: str
    description: Optional[str]
    primary_language: Optional[str]
    topics: list[str]
    stars: int
    forks: int
    contributors_count: Optional[int]
    created_at: str
    pushed_at: str
    license: Optional[str]
    readme_excerpt: Optional[str]
    sources: list[str]
    hn_url: Optional[str] = None
    hn_points: Optional[int] = None
    hn_comments: Optional[int] = None
    reddit_url: Optional[str] = None
    reddit_score: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)
