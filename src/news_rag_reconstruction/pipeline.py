"""RECONSTRUCTED v1 single-vector indexing pipeline with dependency injection."""

from dataclasses import dataclass

from news_rag_reconstruction.chunking import CharacterChunker
from news_rag_reconstruction.embeddings import EmbeddingProvider
from news_rag_reconstruction.models import Article, VectorPayload, VectorPoint
from news_rag_reconstruction.point_ids import PointIdStrategy


@dataclass(frozen=True, slots=True)
class V1IndexingPipeline:
    """Transform one article into internal single-vector point DTOs."""

    chunker: CharacterChunker
    embedding_provider: EmbeddingProvider
    point_id_strategy: PointIdStrategy

    def build_points(self, article: Article) -> tuple[VectorPoint, ...]:
        """Build deterministic points without reading or writing external services."""

        chunks = self.chunker.chunk(article)
        if not chunks:
            return ()

        vectors = tuple(self.embedding_provider.embed_texts([chunk.text for chunk in chunks]))
        if len(vectors) != len(chunks):
            raise ValueError(
                "embedding provider must return one vector per input text; "
                f"received {len(vectors)} vectors for {len(chunks)} texts"
            )

        return tuple(
            VectorPoint(
                point_id=self.point_id_strategy.create(chunk.article_id, chunk.chunk_index),
                vector=vector,
                payload=VectorPayload(
                    article_id=chunk.article_id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    title=chunk.title,
                    organization=chunk.organization,
                    published_at=chunk.published_at,
                    reconstruction_status="RECONSTRUCTED",
                ),
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        )
