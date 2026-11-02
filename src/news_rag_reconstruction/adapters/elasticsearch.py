"""RECONSTRUCTED Elasticsearch adapters; historical mapping and helper options are unresolved."""

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk, scan

from news_rag_reconstruction.models import Article


@dataclass(frozen=True, slots=True)
class SourceFieldMapping:
    """Caller-supplied Source ES field names; no historical defaults are selected."""

    article_id: str | None
    title: str
    content: str
    organization: str | None
    published_at: str | None


@dataclass(frozen=True, slots=True)
class ElasticsearchArticleSource:
    """Read normalized articles from an explicitly configured ES scan."""

    client: Elasticsearch
    index: str
    query: Mapping[str, Any]
    fields: SourceFieldMapping

    def iter_articles(self) -> Iterator[Article]:
        for hit in scan(
            self.client,
            index=self.index,
            query=dict(self.query),
        ):
            yield self._article_from_hit(hit)

    def _article_from_hit(self, hit: Mapping[str, Any]) -> Article:
        source_value = hit.get("_source")
        if not isinstance(source_value, Mapping):
            raise ValueError("hit must contain an object _source")
        source: Mapping[str, Any] = source_value

        article_id = (
            self._required_text(source, self.fields.article_id)
            if self.fields.article_id is not None
            else self._required_text(hit, "_id")
        )
        published_at_text = self._optional_text(source, self.fields.published_at)
        try:
            published_at = (
                datetime.fromisoformat(published_at_text) if published_at_text is not None else None
            )
        except ValueError as error:
            raise ValueError("published_at must be an ISO 8601 string") from error

        return Article(
            article_id=article_id,
            title=self._required_text(source, self.fields.title),
            content=self._required_text(source, self.fields.content),
            organization=self._optional_text(source, self.fields.organization),
            published_at=published_at,
        )

    @staticmethod
    def _required_text(record: Mapping[str, Any], field: str) -> str:
        value = record.get(field)
        if not isinstance(value, str):
            raise ValueError(f"{field} must be a string")
        return value

    @staticmethod
    def _optional_text(record: Mapping[str, Any], field: str | None) -> str | None:
        if field is None:
            return None
        value = record.get(field)
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(f"{field} must be a string or null")
        return value


@dataclass(frozen=True, slots=True)
class ElasticsearchArticleSink:
    """Write a reconstructed article-level search document shape."""

    client: Elasticsearch
    index: str

    def write_articles(self, articles: Sequence[Article]) -> None:
        actions = [self._action(article) for article in articles]
        if not actions:
            return
        bulk(self.client, actions)

    def _action(self, article: Article) -> dict[str, Any]:
        return {
            "_op_type": "index",
            "_index": self.index,
            "_id": article.article_id,
            "_source": {
                "article_id": article.article_id,
                "title": article.title,
                "content": article.content,
                "organization": article.organization,
                "published_at": (
                    article.published_at.isoformat() if article.published_at is not None else None
                ),
                "reconstruction_status": "RECONSTRUCTED",
            },
        }
