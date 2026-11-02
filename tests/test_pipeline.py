from collections.abc import Sequence
from uuid import UUID

import pytest

from news_rag_reconstruction.chunking import CharacterChunker
from news_rag_reconstruction.embeddings import FixtureEmbeddingProvider
from news_rag_reconstruction.models import Article, EmbeddingVector
from news_rag_reconstruction.pipeline import V1IndexingPipeline
from news_rag_reconstruction.point_ids import UUID5PointIdStrategy


def _pipeline() -> V1IndexingPipeline:
    return V1IndexingPipeline(
        chunker=CharacterChunker(chunk_size=18, chunk_overlap=4),
        embedding_provider=FixtureEmbeddingProvider(dimension=6),
        point_id_strategy=UUID5PointIdStrategy(
            namespace=UUID("26bd8e6a-d9e1-45e7-9271-5dfacac81e76")
        ),
    )


def test_fixture_includes_general_short_empty_and_repeat_cases(
    fixture_articles: tuple[Article, ...],
) -> None:
    article_ids = [article.article_id for article in fixture_articles]

    assert "fixture-general-001" in article_ids
    assert "fixture-short-001" in article_ids
    assert "fixture-empty-001" in article_ids
    assert article_ids.count("fixture-repeat-001") == 2


def test_article_is_transformed_to_vector_points_end_to_end(
    fixture_articles: tuple[Article, ...],
) -> None:
    article = fixture_articles[0]

    points = _pipeline().build_points(article)

    assert len(points) > 1
    assert [point.payload.chunk_index for point in points] == list(range(len(points)))
    assert all(point.payload.article_id == article.article_id for point in points)
    assert all(point.payload.title == article.title for point in points)
    assert all(point.payload.organization == article.organization for point in points)
    assert all(point.payload.published_at == article.published_at for point in points)
    assert "".join(point.payload.text for point in points).startswith(article.content[:18])


def test_same_article_transformed_twice_has_identical_results(
    fixture_articles: tuple[Article, ...],
) -> None:
    repeated = [
        article for article in fixture_articles if article.article_id == "fixture-repeat-001"
    ]
    pipeline = _pipeline()

    assert pipeline.build_points(repeated[0]) == pipeline.build_points(repeated[1])


def test_every_point_contains_one_unnamed_dense_vector(
    fixture_articles: tuple[Article, ...],
) -> None:
    points = _pipeline().build_points(fixture_articles[0])

    assert all(isinstance(point.vector, EmbeddingVector) for point in points)
    assert all(len(point.vector.values) == 6 for point in points)
    assert all(not hasattr(point, "vectors") for point in points)


def test_payload_marks_every_point_as_reconstructed(
    fixture_articles: tuple[Article, ...],
) -> None:
    points = _pipeline().build_points(fixture_articles[0])

    assert all(point.payload.reconstruction_status == "RECONSTRUCTED" for point in points)


def test_empty_article_produces_no_points(fixture_articles: tuple[Article, ...]) -> None:
    empty_article = next(
        article for article in fixture_articles if article.article_id == "fixture-empty-001"
    )

    assert _pipeline().build_points(empty_article) == ()


def test_pipeline_rejects_missing_embedding_vectors() -> None:
    class MissingVectorProvider:
        def embed_texts(self, texts: Sequence[str]) -> tuple[EmbeddingVector, ...]:
            return ()

    pipeline = V1IndexingPipeline(
        chunker=CharacterChunker(chunk_size=3, chunk_overlap=0),
        embedding_provider=MissingVectorProvider(),
        point_id_strategy=UUID5PointIdStrategy(
            namespace=UUID("26bd8e6a-d9e1-45e7-9271-5dfacac81e76")
        ),
    )
    article = Article(
        article_id="article-1",
        title="Fixture headline",
        content="abcde",
        organization=None,
        published_at=None,
    )

    with pytest.raises(
        ValueError,
        match=(
            "embedding provider must return one vector per input text; "
            "received 0 vectors for 2 texts"
        ),
    ):
        pipeline.build_points(article)
