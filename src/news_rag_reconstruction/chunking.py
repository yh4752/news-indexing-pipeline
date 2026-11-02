"""RECONSTRUCTED character chunking; historical parameter values remain unresolved."""

from dataclasses import dataclass

from news_rag_reconstruction.models import Article, Chunk


@dataclass(frozen=True, slots=True)
class CharacterChunker:
    """Split article content at deterministic character offsets.

    Empty article content produces no chunks. The caller must provide both
    parameters because no historical default has been confirmed.
    """

    chunk_size: int
    chunk_overlap: int

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")
        if self.chunk_overlap < 0 or self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                "chunk_overlap must be greater than or equal to 0 and less than chunk_size"
            )

    def chunk(self, article: Article) -> tuple[Chunk, ...]:
        """Return ordered chunks while preserving the final content remainder."""

        if not article.content:
            return ()

        chunks: list[Chunk] = []
        start = 0
        step = self.chunk_size - self.chunk_overlap

        while start < len(article.content):
            end = min(start + self.chunk_size, len(article.content))
            chunks.append(
                Chunk(
                    article_id=article.article_id,
                    chunk_index=len(chunks),
                    text=article.content[start:end],
                    title=article.title,
                    organization=article.organization,
                    published_at=article.published_at,
                )
            )
            if end == len(article.content):
                break
            start += step

        return tuple(chunks)
