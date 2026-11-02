from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import Mock

import pytest
from elasticsearch import Elasticsearch

import news_rag_reconstruction.adapters.elasticsearch as adapter_module
from news_rag_reconstruction.adapters.elasticsearch import (
    ElasticsearchArticleSink,
    ElasticsearchArticleSource,
    SourceFieldMapping,
)
from news_rag_reconstruction.models import Article


def _client() -> Elasticsearch:
    return cast(Elasticsearch, Mock())


def _fields() -> SourceFieldMapping:
    return SourceFieldMapping(
        article_id=None,
        title="headline",
        content="body",
        organization="publisher",
        published_at="published_at",
    )


def test_source_supplies_explicit_index_and_query_to_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hits: Iterable[dict[str, Any]] = [
        {
            "_id": "article-1",
            "_source": {
                "headline": "Fixture headline",
                "body": "Fixture content",
                "publisher": "Fixture News",
                "published_at": "2026-01-15T09:00:00+09:00",
            },
        }
    ]
    scan_mock = Mock(return_value=hits)
    monkeypatch.setattr(adapter_module, "scan", scan_mock)
    query: dict[str, Any] = {"query": {"match_all": {}}}

    articles = tuple(
        ElasticsearchArticleSource(
            client=_client(),
            index="source-news",
            query=query,
            fields=_fields(),
        ).iter_articles()
    )

    assert articles[0].article_id == "article-1"
    assert articles[0].title == "Fixture headline"
    assert articles[0].content == "Fixture content"
    assert articles[0].organization == "Fixture News"
    assert articles[0].published_at == datetime.fromisoformat("2026-01-15T09:00:00+09:00")
    assert scan_mock.call_args.kwargs["index"] == "source-news"
    assert scan_mock.call_args.kwargs["query"] == query


def test_source_can_read_article_id_from_an_explicit_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scan_mock = Mock(
        return_value=[
            {
                "_id": "ignored-es-id",
                "_source": {
                    "news_id": "domain-id",
                    "headline": "Headline",
                    "body": "Body",
                },
            }
        ]
    )
    monkeypatch.setattr(adapter_module, "scan", scan_mock)
    fields = SourceFieldMapping(
        article_id="news_id",
        title="headline",
        content="body",
        organization=None,
        published_at=None,
    )

    article = next(
        iter(
            ElasticsearchArticleSource(
                client=_client(),
                index="source-news",
                query={"query": {"match_all": {}}},
                fields=fields,
            ).iter_articles()
        )
    )

    assert article.article_id == "domain-id"
    assert article.organization is None
    assert article.published_at is None


def test_source_rejects_a_hit_without_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapter_module, "scan", Mock(return_value=[{"_id": "article-1"}]))
    source = ElasticsearchArticleSource(
        client=_client(),
        index="source-news",
        query={"query": {"match_all": {}}},
        fields=_fields(),
    )

    with pytest.raises(ValueError, match="hit must contain an object _source"):
        tuple(source.iter_articles())


def test_source_rejects_a_non_iso_published_at(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        adapter_module,
        "scan",
        Mock(
            return_value=[
                {
                    "_id": "article-1",
                    "_source": {
                        "headline": "Headline",
                        "body": "Body",
                        "publisher": None,
                        "published_at": "not-a-date",
                    },
                }
            ]
        ),
    )
    source = ElasticsearchArticleSource(
        client=_client(),
        index="source-news",
        query={"query": {"match_all": {}}},
        fields=_fields(),
    )

    with pytest.raises(ValueError, match="published_at must be an ISO 8601 string"):
        tuple(source.iter_articles())


def test_article_sink_writes_article_level_bulk_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bulk_mock = Mock(return_value=(1, []))
    monkeypatch.setattr(adapter_module, "bulk", bulk_mock)
    article = Article(
        article_id="article-1",
        title="Fixture headline",
        content="Fixture content",
        organization="Fixture News",
        published_at=datetime(2026, 1, 15, tzinfo=UTC),
    )

    ElasticsearchArticleSink(client=_client(), index="search-news").write_articles([article])

    actions = bulk_mock.call_args.args[1]
    assert actions == [
        {
            "_op_type": "index",
            "_index": "search-news",
            "_id": "article-1",
            "_source": {
                "article_id": "article-1",
                "title": "Fixture headline",
                "content": "Fixture content",
                "organization": "Fixture News",
                "published_at": "2026-01-15T00:00:00+00:00",
                "reconstruction_status": "RECONSTRUCTED",
            },
        }
    ]


def test_article_sink_skips_an_empty_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    bulk_mock = Mock()
    monkeypatch.setattr(adapter_module, "bulk", bulk_mock)

    ElasticsearchArticleSink(client=_client(), index="search-news").write_articles([])

    bulk_mock.assert_not_called()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("headline", None, "headline must be a string"),
        ("body", 123, "body must be a string"),
        ("publisher", [], "publisher must be a string or null"),
        ("published_at", 123, "published_at must be a string or null"),
    ],
)
def test_source_rejects_invalid_field_types(
    monkeypatch: pytest.MonkeyPatch, field: str, value: Any, message: str
) -> None:
    record: dict[str, Any] = {"headline": "Headline", "body": "Body"}
    record[field] = value
    monkeypatch.setattr(
        adapter_module, "scan", Mock(return_value=[{"_id": "article-1", "_source": record}])
    )
    source = ElasticsearchArticleSource(
        client=_client(), index="source-news", query={"query": {"match_all": {}}}, fields=_fields()
    )

    with pytest.raises(ValueError, match=message):
        tuple(source.iter_articles())


def test_article_sink_preserves_missing_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    bulk_mock = Mock(return_value=(1, []))
    monkeypatch.setattr(adapter_module, "bulk", bulk_mock)
    article = Article("article-1", "Title", "", None, None)

    ElasticsearchArticleSink(client=_client(), index="search-news").write_articles([article])

    document = bulk_mock.call_args.args[1][0]["_source"]
    assert document["content"] == ""
    assert document["organization"] is None
    assert document["published_at"] is None


def test_article_sink_propagates_bulk_item_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    from elasticsearch.helpers import BulkIndexError

    failure = BulkIndexError("fixture bulk failure", [{"index": {"status": 400}}])
    monkeypatch.setattr(adapter_module, "bulk", Mock(side_effect=failure))

    with pytest.raises(BulkIndexError) as caught:
        ElasticsearchArticleSink(client=_client(), index="search-news").write_articles(
            [Article("article-1", "Title", "Body", None, None)]
        )

    assert caught.value is failure


def test_source_is_lazy_and_propagates_scan_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def hits() -> Iterable[dict[str, Any]]:
        yield {"_id": "article-1", "_source": {"headline": "Title", "body": "Body"}}
        raise RuntimeError("fixture scan failure")

    scan_mock = Mock(return_value=hits())
    monkeypatch.setattr(adapter_module, "scan", scan_mock)
    source = ElasticsearchArticleSource(
        client=_client(), index="source-news", query={"query": {"match_all": {}}}, fields=_fields()
    )
    articles = iter(source.iter_articles())
    scan_mock.assert_not_called()
    assert next(articles).article_id == "article-1"
    with pytest.raises(RuntimeError, match="fixture scan failure"):
        next(articles)
