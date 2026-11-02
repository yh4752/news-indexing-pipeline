from inspect import Parameter, signature

import pytest

from news_rag_reconstruction.embeddings import FixtureEmbeddingProvider


@pytest.mark.parametrize("dimension", [0, -1])
def test_fixture_embedding_rejects_non_positive_dimension(dimension: int) -> None:
    with pytest.raises(ValueError, match="dimension must be greater than 0"):
        FixtureEmbeddingProvider(dimension=dimension)


def test_fixture_embedding_dimension_is_a_required_constructor_argument() -> None:
    assert signature(FixtureEmbeddingProvider).parameters["dimension"].default is Parameter.empty


def test_fixture_embedding_is_deterministic_for_the_same_text() -> None:
    provider = FixtureEmbeddingProvider(dimension=4)

    assert provider.embed_texts(["same text"]) == provider.embed_texts(["same text"])


def test_fixture_embedding_returns_the_requested_dimension() -> None:
    vectors = FixtureEmbeddingProvider(dimension=5).embed_texts(["first", "second"])

    assert len(vectors) == 2
    assert all(len(vector.values) == 5 for vector in vectors)


def test_fixture_embedding_preserves_input_order() -> None:
    provider = FixtureEmbeddingProvider(dimension=3)

    assert provider.embed_texts(["first", "second"]) == (
        provider.embed_texts(["first"])[0],
        provider.embed_texts(["second"])[0],
    )
