from collections.abc import Iterable, Sequence
from contextlib import closing
from dataclasses import dataclass, field
from typing import Any, cast
from unittest.mock import Mock
from uuid import UUID

import pytest
from elasticsearch import Elasticsearch
from qdrant_client import QdrantClient, models

import news_rag_reconstruction.adapters.elasticsearch as es_adapter
from news_rag_reconstruction.adapters.elasticsearch import (
    ElasticsearchArticleSink,
    ElasticsearchArticleSource,
    SourceFieldMapping,
)
from news_rag_reconstruction.adapters.qdrant import QdrantVectorPointSink
from news_rag_reconstruction.batch import V1BatchIndexer
from news_rag_reconstruction.chunking import CharacterChunker
from news_rag_reconstruction.embeddings import FixtureEmbeddingProvider
from news_rag_reconstruction.models import Article, EmbeddingVector, VectorPoint
from news_rag_reconstruction.pipeline import V1IndexingPipeline
from news_rag_reconstruction.point_ids import UUID5PointIdStrategy


@dataclass
class RecordingSource:
    articles: tuple[Article, ...]

    def iter_articles(self) -> Iterable[Article]:
        return self.articles


@dataclass
class RecordingArticleSink:
    batches: list[tuple[Article, ...]] = field(default_factory=list)

    def write_articles(self, articles: Sequence[Article]) -> None:
        self.batches.append(tuple(articles))


@dataclass
class RecordingPointSink:
    batches: list[tuple[VectorPoint, ...]] = field(default_factory=list)

    def upsert_points(self, points: Sequence[VectorPoint]) -> None:
        self.batches.append(tuple(points))


def _pipeline() -> V1IndexingPipeline:
    return V1IndexingPipeline(
        chunker=CharacterChunker(chunk_size=100, chunk_overlap=0),
        embedding_provider=FixtureEmbeddingProvider(dimension=3),
        point_id_strategy=UUID5PointIdStrategy(
            namespace=UUID("26bd8e6a-d9e1-45e7-9271-5dfacac81e76")
        ),
    )


def test_batch_indexer_bounds_writes_and_returns_counts(
    fixture_articles: tuple[Article, ...],
) -> None:
    source = RecordingSource(fixture_articles[:4])
    article_sink = RecordingArticleSink()
    point_sink = RecordingPointSink()

    result = V1BatchIndexer(
        source=source,
        article_sink=article_sink,
        point_sink=point_sink,
        pipeline=_pipeline(),
        batch_size=2,
    ).run()

    assert [len(batch) for batch in article_sink.batches] == [2, 2]
    assert result.batches_completed == 2
    assert result.articles_written == 4
    assert result.points_written == sum(len(batch) for batch in point_sink.batches)


def test_empty_source_makes_no_writes() -> None:
    article_sink = RecordingArticleSink()
    point_sink = RecordingPointSink()

    result = V1BatchIndexer(
        source=RecordingSource(()),
        article_sink=article_sink,
        point_sink=point_sink,
        pipeline=_pipeline(),
        batch_size=2,
    ).run()

    assert result.batches_completed == 0
    assert result.articles_written == 0
    assert result.points_written == 0
    assert article_sink.batches == []
    assert point_sink.batches == []


def test_empty_content_is_written_to_es_but_not_qdrant(
    fixture_articles: tuple[Article, ...],
) -> None:
    empty = next(article for article in fixture_articles if not article.content)
    article_sink = RecordingArticleSink()
    point_sink = RecordingPointSink()

    result = V1BatchIndexer(
        source=RecordingSource((empty,)),
        article_sink=article_sink,
        point_sink=point_sink,
        pipeline=_pipeline(),
        batch_size=1,
    ).run()

    assert article_sink.batches == [(empty,)]
    assert point_sink.batches == []
    assert result.articles_written == 1
    assert result.points_written == 0


def test_rejects_non_positive_batch_size() -> None:
    with pytest.raises(ValueError, match="batch_size must be greater than 0"):
        V1BatchIndexer(
            source=RecordingSource(()),
            article_sink=RecordingArticleSink(),
            point_sink=RecordingPointSink(),
            pipeline=_pipeline(),
            batch_size=0,
        )


def test_qdrant_failure_leaves_the_completed_es_write_visible(
    fixture_articles: tuple[Article, ...],
) -> None:
    class FailingPointSink:
        def upsert_points(self, points: Sequence[VectorPoint]) -> None:
            raise RuntimeError("fixture qdrant failure")

    article = fixture_articles[0]
    article_sink = RecordingArticleSink()
    indexer = V1BatchIndexer(
        source=RecordingSource((article,)),
        article_sink=article_sink,
        point_sink=FailingPointSink(),
        pipeline=_pipeline(),
        batch_size=1,
    )

    with pytest.raises(RuntimeError, match="fixture qdrant failure"):
        indexer.run()

    assert article_sink.batches == [(article,)]


def test_batch_indexer_streams_and_flushes_the_final_partial_batch(
    fixture_articles: tuple[Article, ...],
) -> None:
    article_sink = RecordingArticleSink()
    point_sink = RecordingPointSink()

    class StreamingSource:
        def iter_articles(self) -> Iterable[Article]:
            yield from fixture_articles[:2]
            assert len(article_sink.batches) == 1
            yield fixture_articles[2]

    result = V1BatchIndexer(StreamingSource(), article_sink, point_sink, _pipeline(), 2).run()

    assert [len(batch) for batch in article_sink.batches] == [2, 1]
    assert result.batches_completed == 2
    assert result.articles_written == 3


def test_embedding_failure_makes_no_destination_writes(
    fixture_articles: tuple[Article, ...],
) -> None:
    class FailingEmbeddings:
        def embed_texts(self, texts: Sequence[str]) -> Sequence[EmbeddingVector]:
            raise RuntimeError("fixture embedding failure")

    pipeline = _pipeline()
    pipeline = V1IndexingPipeline(pipeline.chunker, FailingEmbeddings(), pipeline.point_id_strategy)
    article_sink = RecordingArticleSink()
    point_sink = RecordingPointSink()

    with pytest.raises(RuntimeError, match="fixture embedding failure"):
        V1BatchIndexer(
            RecordingSource(fixture_articles[:1]), article_sink, point_sink, pipeline, 1
        ).run()

    assert article_sink.batches == []
    assert point_sink.batches == []


def test_es_failure_stops_before_qdrant_or_the_next_batch(
    fixture_articles: tuple[Article, ...],
) -> None:
    class FailingArticles:
        calls = 0

        def write_articles(self, articles: Sequence[Article]) -> None:
            self.calls += 1
            raise RuntimeError("fixture ES failure")

    article_sink = FailingArticles()
    point_sink = RecordingPointSink()
    with pytest.raises(RuntimeError, match="fixture ES failure"):
        V1BatchIndexer(
            RecordingSource(fixture_articles[:2]), article_sink, point_sink, _pipeline(), 1
        ).run()

    assert article_sink.calls == 1
    assert point_sink.batches == []


def test_offline_adapter_chain_stores_serialized_points_in_qdrant_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Explicit fixture settings; no live services or historical collection settings.
    monkeypatch.setattr(
        es_adapter,
        "scan",
        Mock(return_value=[{"_id": "fixture-id", "_source": {"title": "Title", "body": "Body"}}]),
    )
    documents: list[dict[str, Any]] = []

    def record_bulk(client: Elasticsearch, actions: list[dict[str, Any]]) -> tuple[int, list[Any]]:
        documents.extend(actions)
        return len(actions), []

    monkeypatch.setattr(es_adapter, "bulk", record_bulk)
    es_client = cast(Elasticsearch, Mock())
    with closing(QdrantClient(":memory:")) as qdrant:
        qdrant.create_collection(
            collection_name="fixture-v1",
            vectors_config=models.VectorParams(size=3, distance=models.Distance.COSINE),
        )
        result = V1BatchIndexer(
            source=ElasticsearchArticleSource(
                es_client,
                "fixture-source",
                {"query": {"match_all": {}}},
                SourceFieldMapping(None, "title", "body", None, None),
            ),
            article_sink=ElasticsearchArticleSink(es_client, "fixture-search"),
            point_sink=QdrantVectorPointSink(qdrant, "fixture-v1"),
            pipeline=_pipeline(),
            batch_size=1,
        ).run()
        records, _ = qdrant.scroll("fixture-v1", with_vectors=True)

    assert result.articles_written == result.points_written == 1
    assert documents[0]["_id"] == "fixture-id"
    assert documents[0]["_source"]["content"] == "Body"
    assert len(records) == 1
    expected = _pipeline().build_points(Article("fixture-id", "Title", "Body", None, None))[0]
    assert records[0].id == expected.point_id
    assert records[0].payload is not None
    assert records[0].payload["article_id"] == "fixture-id"
    assert records[0].payload["reconstruction_status"] == "RECONSTRUCTED"
    assert isinstance(records[0].vector, list)
    assert len(records[0].vector) == 3


def test_qdrant_wait_timeout_stops_the_batch_after_es_write(
    fixture_articles: tuple[Article, ...],
) -> None:
    client = Mock()
    client.upsert.return_value = models.UpdateResult(
        operation_id=1, status=models.UpdateStatus.WAIT_TIMEOUT
    )
    article_sink = RecordingArticleSink()
    article = fixture_articles[0]
    with pytest.raises(RuntimeError, match="Qdrant upsert did not complete: wait_timeout"):
        V1BatchIndexer(
            RecordingSource((article,)),
            article_sink,
            QdrantVectorPointSink(cast(QdrantClient, client), "fixture-v1"),
            _pipeline(),
            1,
        ).run()
    assert article_sink.batches == [(article,)]
