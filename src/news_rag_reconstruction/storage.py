"""RECONSTRUCTED storage ports; historical client and batching details remain unresolved."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol

from news_rag_reconstruction.models import Article, VectorPoint


class ArticleSource(Protocol):
    """Yield normalized articles from an external source."""

    def iter_articles(self) -> Iterable[Article]:
        """Yield articles without promising historical ordering."""
        ...


class ArticleSink(Protocol):
    """Write article-level search documents."""

    def write_articles(self, articles: Sequence[Article]) -> None:
        """Write one bounded article batch."""
        ...


class VectorPointSink(Protocol):
    """Write internal single-vector points."""

    def upsert_points(self, points: Sequence[VectorPoint]) -> None:
        """Upsert one bounded point batch."""
        ...


@dataclass(frozen=True, slots=True)
class BatchIndexingResult:
    """Counts returned only after every sink call in completed batches succeeds."""

    batches_completed: int
    articles_written: int
    points_written: int
