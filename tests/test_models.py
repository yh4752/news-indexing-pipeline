from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from news_rag_reconstruction.models import (
    Article,
    Chunk,
    EmbeddingVector,
    VectorPayload,
    VectorPoint,
)


def test_article_is_immutable() -> None:
    article = Article(
        article_id="article-1",
        title="Fixture headline",
        content="Fixture content",
        organization="Fixture News",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    with pytest.raises(FrozenInstanceError):
        article.title = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("instance", "field_name", "replacement"),
    [
        (
            Chunk(
                article_id="article-1",
                chunk_index=0,
                text="Fixture content",
                title="Fixture headline",
                organization=None,
                published_at=None,
            ),
            "text",
            "Changed",
        ),
        (EmbeddingVector(values=(0.1,)), "values", (0.2,)),
        (
            VectorPayload(
                article_id="article-1",
                chunk_index=0,
                text="Fixture content",
                title="Fixture headline",
                organization=None,
                published_at=None,
                reconstruction_status="RECONSTRUCTED",
            ),
            "title",
            "Changed",
        ),
        (
            VectorPoint(
                point_id="point-1",
                vector=EmbeddingVector(values=(0.1,)),
                payload=VectorPayload(
                    article_id="article-1",
                    chunk_index=0,
                    text="Fixture content",
                    title="Fixture headline",
                    organization=None,
                    published_at=None,
                    reconstruction_status="RECONSTRUCTED",
                ),
            ),
            "point_id",
            "changed-point",
        ),
    ],
)
def test_remaining_domain_models_are_immutable(
    instance: object,
    field_name: str,
    replacement: object,
) -> None:
    with pytest.raises(FrozenInstanceError):
        setattr(instance, field_name, replacement)


def test_vector_point_keeps_a_single_vector_and_structured_payload() -> None:
    payload = VectorPayload(
        article_id="article-1",
        chunk_index=0,
        text="Fixture content",
        title="Fixture headline",
        organization=None,
        published_at=None,
        reconstruction_status="RECONSTRUCTED",
    )

    point = VectorPoint(
        point_id="point-1",
        vector=EmbeddingVector(values=(0.1, 0.2)),
        payload=payload,
    )

    assert point.vector.values == (0.1, 0.2)
    assert point.payload == payload


@pytest.mark.parametrize("point_id", ["point-1", 42])
def test_vector_point_accepts_supported_point_id_types(point_id: str | int) -> None:
    point = VectorPoint(
        point_id=point_id,
        vector=EmbeddingVector(values=(0.1,)),
        payload=VectorPayload(
            article_id="article-1",
            chunk_index=0,
            text="Fixture content",
            title="Fixture headline",
            organization=None,
            published_at=None,
            reconstruction_status="RECONSTRUCTED",
        ),
    )

    assert point.point_id == point_id
