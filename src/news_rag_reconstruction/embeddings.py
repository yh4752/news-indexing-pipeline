"""RECONSTRUCTED embedding contracts and an offline test-only fixture provider."""

from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import shake_256
from typing import Protocol

from news_rag_reconstruction.models import EmbeddingVector


class EmbeddingProvider(Protocol):
    """Provider-independent text embedding contract."""

    def embed_texts(self, texts: Sequence[str]) -> Sequence[EmbeddingVector]:
        """Embed texts in input order."""
        ...


@dataclass(frozen=True, slots=True)
class FixtureEmbeddingProvider:
    """Create deterministic vectors for tests without network access.

    The generated values do not imitate or identify any historical embedding model.
    """

    dimension: int

    def __post_init__(self) -> None:
        if self.dimension <= 0:
            raise ValueError("dimension must be greater than 0")

    def embed_texts(self, texts: Sequence[str]) -> tuple[EmbeddingVector, ...]:
        """Return one deterministic fixture vector for each input string."""

        return tuple(self._embed_text(text) for text in texts)

    def _embed_text(self, text: str) -> EmbeddingVector:
        digest = shake_256(text.encode("utf-8")).digest(self.dimension * 8)
        denominator = float((1 << 64) - 1)
        values = tuple(
            int.from_bytes(digest[offset : offset + 8], byteorder="big") / denominator
            for offset in range(0, len(digest), 8)
        )
        return EmbeddingVector(values=values)
