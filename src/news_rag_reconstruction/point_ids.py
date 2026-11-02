"""RECONSTRUCTED point ID contracts; the historical final strategy remains unresolved."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID, uuid5

from news_rag_reconstruction.models import PointId


class PointIdStrategy(Protocol):
    """Create a point ID for an article chunk."""

    def create(self, article_id: str, chunk_index: int) -> PointId:
        """Return a stable point ID for the supplied inputs."""
        ...


@dataclass(frozen=True, slots=True)
class UUID5PointIdStrategy:
    """Current reconstruction-only UUID5 strategy with an explicit namespace."""

    namespace: UUID

    def create(self, article_id: str, chunk_index: int) -> str:
        """Create a deterministic UUID5 string without claiming historical use."""

        name = f"{len(article_id)}:{article_id}:{chunk_index}"
        return str(uuid5(self.namespace, name))
