"""RECONSTRUCTED immutable DTOs; these are not claimed as historical source code."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias

PointId: TypeAlias = str | int


@dataclass(frozen=True, slots=True)
class Article:
    """Input article used by the reconstructed indexing core."""

    article_id: str
    title: str
    content: str
    organization: str | None
    published_at: datetime | None


@dataclass(frozen=True, slots=True)
class Chunk:
    """Character-based article segment with inherited article metadata."""

    article_id: str
    chunk_index: int
    text: str
    title: str
    organization: str | None
    published_at: datetime | None


@dataclass(frozen=True, slots=True)
class EmbeddingVector:
    """Provider-independent dense vector."""

    values: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class VectorPayload:
    """Structured metadata stored alongside one reconstructed vector point."""

    article_id: str
    chunk_index: int
    text: str
    title: str
    organization: str | None
    published_at: datetime | None
    reconstruction_status: Literal["RECONSTRUCTED"]


@dataclass(frozen=True, slots=True)
class VectorPoint:
    """Internal single-vector DTO with no Qdrant SDK dependency."""

    point_id: PointId
    vector: EmbeddingVector
    payload: VectorPayload
