from inspect import Parameter, signature

import pytest

from news_rag_reconstruction.chunking import CharacterChunker
from news_rag_reconstruction.models import Article


def _article(content: str) -> Article:
    return Article(
        article_id="article-1",
        title="Fixture headline",
        content=content,
        organization="Fixture News",
        published_at=None,
    )


def test_rejects_non_positive_chunk_size() -> None:
    with pytest.raises(ValueError, match="chunk_size must be greater than 0"):
        CharacterChunker(chunk_size=0, chunk_overlap=0)


def test_chunk_parameters_are_required_constructor_arguments() -> None:
    parameters = signature(CharacterChunker).parameters

    assert parameters["chunk_size"].default is Parameter.empty
    assert parameters["chunk_overlap"].default is Parameter.empty


@pytest.mark.parametrize("overlap", [-1, 4])
def test_rejects_overlap_outside_valid_range(overlap: int) -> None:
    with pytest.raises(
        ValueError,
        match="chunk_overlap must be greater than or equal to 0 and less than chunk_size",
    ):
        CharacterChunker(chunk_size=4, chunk_overlap=overlap)


def test_short_body_produces_one_complete_chunk() -> None:
    chunks = CharacterChunker(chunk_size=10, chunk_overlap=2).chunk(_article("short"))

    assert [chunk.text for chunk in chunks] == ["short"]
    assert [chunk.chunk_index for chunk in chunks] == [0]


def test_overlap_is_applied_at_chunk_boundaries() -> None:
    chunks = CharacterChunker(chunk_size=4, chunk_overlap=1).chunk(_article("abcdefghij"))

    assert [chunk.text for chunk in chunks] == ["abcd", "defg", "ghij"]


def test_last_chunk_is_preserved_without_padding_or_truncation() -> None:
    chunks = CharacterChunker(chunk_size=4, chunk_overlap=0).chunk(_article("abcdef"))

    assert [chunk.text for chunk in chunks] == ["abcd", "ef"]


def test_empty_body_produces_no_chunks() -> None:
    chunks = CharacterChunker(chunk_size=4, chunk_overlap=1).chunk(_article(""))

    assert chunks == ()


def test_same_input_produces_the_same_chunk_sequence() -> None:
    chunker = CharacterChunker(chunk_size=4, chunk_overlap=1)
    article = _article("abcdefghij")

    assert chunker.chunk(article) == chunker.chunk(article)
