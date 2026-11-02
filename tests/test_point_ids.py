from inspect import Parameter, signature
from uuid import UUID

from news_rag_reconstruction.point_ids import UUID5PointIdStrategy


def test_uuid5_point_id_is_deterministic() -> None:
    strategy = UUID5PointIdStrategy(namespace=UUID("26bd8e6a-d9e1-45e7-9271-5dfacac81e76"))

    assert strategy.create("article-1", 0) == strategy.create("article-1", 0)


def test_uuid5_namespace_is_a_required_constructor_argument() -> None:
    assert signature(UUID5PointIdStrategy).parameters["namespace"].default is Parameter.empty


def test_same_article_id_and_chunk_index_have_the_same_id() -> None:
    strategy = UUID5PointIdStrategy(namespace=UUID("26bd8e6a-d9e1-45e7-9271-5dfacac81e76"))
    first_run = strategy.create(article_id="article-1", chunk_index=2)
    second_run = strategy.create(article_id="article-1", chunk_index=2)

    assert first_run == second_run
    assert UUID(first_run).version == 5


def test_different_chunk_indexes_have_different_ids() -> None:
    strategy = UUID5PointIdStrategy(namespace=UUID("26bd8e6a-d9e1-45e7-9271-5dfacac81e76"))

    assert strategy.create("article-1", 0) != strategy.create("article-1", 1)


def test_different_article_ids_have_different_ids_at_the_same_chunk_index() -> None:
    strategy = UUID5PointIdStrategy(namespace=UUID("26bd8e6a-d9e1-45e7-9271-5dfacac81e76"))

    assert strategy.create("article-1", 0) != strategy.create("article-2", 0)
