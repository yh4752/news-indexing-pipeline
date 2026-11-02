from dataclasses import replace
from datetime import UTC, datetime
from typing import cast
from unittest.mock import Mock

import pytest
from qdrant_client import QdrantClient, models

from news_rag_reconstruction.adapters.qdrant import QdrantVectorPointSink
from news_rag_reconstruction.models import EmbeddingVector, VectorPayload, VectorPoint


def _client() -> tuple[QdrantClient, Mock]:
    client_mock = Mock()
    client_mock.upsert.return_value = models.UpdateResult(
        operation_id=1, status=models.UpdateStatus.COMPLETED
    )
    return cast(QdrantClient, client_mock), client_mock


def _point(point_id: str | int) -> VectorPoint:
    return VectorPoint(
        point_id=point_id,
        vector=EmbeddingVector(values=(0.1, 0.2)),
        payload=VectorPayload(
            article_id="article-1",
            chunk_index=0,
            text="Fixture content",
            title="Fixture headline",
            organization="Fixture News",
            published_at=datetime(2026, 1, 15, tzinfo=UTC),
            reconstruction_status="RECONSTRUCTED",
        ),
    )


def test_qdrant_sink_writes_one_unnamed_dense_vector() -> None:
    client, client_mock = _client()
    point_id = "26bd8e6a-d9e1-45e7-9271-5dfacac81e76"

    QdrantVectorPointSink(client=client, collection_name="news-v1").upsert_points(
        [_point(point_id)]
    )

    kwargs = client_mock.upsert.call_args.kwargs
    assert kwargs["collection_name"] == "news-v1"
    assert kwargs["wait"] is True
    assert len(kwargs["points"]) == 1
    serialized = kwargs["points"][0]
    assert serialized.id == point_id
    assert serialized.vector == [0.1, 0.2]
    assert not isinstance(serialized.vector, dict)
    assert serialized.payload == {
        "article_id": "article-1",
        "chunk_index": 0,
        "text": "Fixture content",
        "title": "Fixture headline",
        "organization": "Fixture News",
        "published_at": "2026-01-15T00:00:00+00:00",
        "reconstruction_status": "RECONSTRUCTED",
    }


def test_qdrant_sink_accepts_an_unsigned_integer_id() -> None:
    client, client_mock = _client()

    QdrantVectorPointSink(client=client, collection_name="news-v1").upsert_points([_point(42)])

    assert client_mock.upsert.call_args.kwargs["points"][0].id == 42


@pytest.mark.parametrize("point_id", ["article-1:0", -1, 2**64, True, False])
def test_qdrant_sink_rejects_ids_outside_qdrant_constraints(point_id: str | int) -> None:
    client, client_mock = _client()
    sink = QdrantVectorPointSink(client=client, collection_name="news-v1")

    with pytest.raises(
        ValueError, match="point ID must be a UUID string or unsigned 64-bit integer"
    ):
        sink.upsert_points([_point(point_id)])

    client_mock.upsert.assert_not_called()


def test_qdrant_sink_skips_an_empty_batch() -> None:
    client, client_mock = _client()

    QdrantVectorPointSink(client=client, collection_name="news-v1").upsert_points([])

    client_mock.upsert.assert_not_called()


@pytest.mark.parametrize("point_id", [0, 2**64 - 1])
def test_qdrant_sink_accepts_integer_id_boundaries(point_id: int) -> None:
    client, client_mock = _client()
    QdrantVectorPointSink(client, "news-v1").upsert_points([_point(point_id)])
    assert client_mock.upsert.call_args.kwargs["points"][0].id == point_id


def test_qdrant_sink_validates_the_whole_batch_before_io() -> None:
    client, client_mock = _client()
    with pytest.raises(ValueError, match="point ID must be"):
        QdrantVectorPointSink(client, "news-v1").upsert_points([_point(42), _point("bad-id")])
    client_mock.upsert.assert_not_called()


def test_qdrant_sink_serializes_null_metadata() -> None:
    client, client_mock = _client()
    point = _point(42)
    point = replace(point, payload=replace(point.payload, organization=None, published_at=None))
    QdrantVectorPointSink(client, "news-v1").upsert_points([point])
    payload = client_mock.upsert.call_args.kwargs["points"][0].payload
    assert payload["organization"] is None
    assert payload["published_at"] is None


def test_qdrant_sink_propagates_client_failure() -> None:
    client, client_mock = _client()
    failure = RuntimeError("fixture upsert failure")
    client_mock.upsert.side_effect = failure
    with pytest.raises(RuntimeError) as caught:
        QdrantVectorPointSink(client, "news-v1").upsert_points([_point(42)])
    assert caught.value is failure


@pytest.mark.parametrize(
    "status", [models.UpdateStatus.ACKNOWLEDGED, models.UpdateStatus.WAIT_TIMEOUT]
)
def test_qdrant_sink_rejects_non_completed_update_results(status: models.UpdateStatus) -> None:
    client, client_mock = _client()
    client_mock.upsert.return_value = models.UpdateResult(operation_id=1, status=status)
    with pytest.raises(RuntimeError, match=f"Qdrant upsert did not complete: {status.value}"):
        QdrantVectorPointSink(client, "news-v1").upsert_points([_point(42)])
