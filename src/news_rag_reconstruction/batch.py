"""RECONSTRUCTED v1 batch coordination; write order and batch size are current choices."""

from dataclasses import dataclass
from itertools import islice

from news_rag_reconstruction.models import Article, VectorPoint
from news_rag_reconstruction.pipeline import V1IndexingPipeline
from news_rag_reconstruction.storage import (
    ArticleSink,
    ArticleSource,
    BatchIndexingResult,
    VectorPointSink,
)


@dataclass(frozen=True, slots=True)
class V1BatchIndexer:
    """Stream source articles through bounded transformation and destination writes."""

    source: ArticleSource
    article_sink: ArticleSink
    point_sink: VectorPointSink
    pipeline: V1IndexingPipeline
    batch_size: int

    def __post_init__(self) -> None:
        if self.batch_size <= 0:
            raise ValueError("batch_size must be greater than 0")

    def run(self) -> BatchIndexingResult:
        iterator = iter(self.source.iter_articles())
        batches_completed = 0
        articles_written = 0
        points_written = 0

        while batch := tuple(islice(iterator, self.batch_size)):
            points = self._build_points(batch)
            self.article_sink.write_articles(batch)
            if points:
                self.point_sink.upsert_points(points)

            batches_completed += 1
            articles_written += len(batch)
            points_written += len(points)

        return BatchIndexingResult(
            batches_completed=batches_completed,
            articles_written=articles_written,
            points_written=points_written,
        )

    def _build_points(self, articles: tuple[Article, ...]) -> tuple[VectorPoint, ...]:
        return tuple(point for article in articles for point in self.pipeline.build_points(article))
