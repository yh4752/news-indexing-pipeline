"""RECONSTRUCTED Qdrant adapter for v1 unnamed single-vector points."""

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from qdrant_client import QdrantClient, models

from news_rag_reconstruction.models import PointId, VectorPoint


@dataclass(frozen=True, slots=True)
class QdrantVectorPointSink:
    """Upsert internal points into a pre-existing reconstructed collection."""

    client: QdrantClient
    collection_name: str

    def upsert_points(self, points: Sequence[VectorPoint]) -> None:
        serialized = [self._serialize(point) for point in points]
        if not serialized:
            return
        result = self.client.upsert(
            collection_name=self.collection_name,
            points=serialized,
            wait=True,
        )
        if result.status != models.UpdateStatus.COMPLETED:
            raise RuntimeError(f"Qdrant upsert did not complete: {result.status.value}")

    def _serialize(self, point: VectorPoint) -> models.PointStruct:
        payload = point.payload
        return models.PointStruct(
            id=self._validated_id(point.point_id),
            vector=list(point.vector.values),
            payload={
                "article_id": payload.article_id,
                "chunk_index": payload.chunk_index,
                "text": payload.text,
                "title": payload.title,
                "organization": payload.organization,
                "published_at": (
                    payload.published_at.isoformat() if payload.published_at is not None else None
                ),
                "reconstruction_status": payload.reconstruction_status,
            },
        )

    @staticmethod
    def _validated_id(point_id: PointId) -> PointId:
        if isinstance(point_id, int) and not isinstance(point_id, bool) and 0 <= point_id < 2**64:
            return point_id
        if isinstance(point_id, str):
            try:
                UUID(point_id)
            except ValueError:
                pass
            else:
                return point_id
        raise ValueError("point ID must be a UUID string or unsigned 64-bit integer")
