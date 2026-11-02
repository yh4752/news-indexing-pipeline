from dataclasses import FrozenInstanceError

import pytest

from news_rag_reconstruction.storage import BatchIndexingResult


def test_batch_indexing_result_is_immutable() -> None:
    result = BatchIndexingResult(batches_completed=1, articles_written=2, points_written=3)

    with pytest.raises(FrozenInstanceError):
        result.points_written = 4  # type: ignore[misc]


def test_batch_indexing_result_keeps_independent_counts() -> None:
    result = BatchIndexingResult(batches_completed=2, articles_written=4, points_written=7)

    assert result.batches_completed == 2
    assert result.articles_written == 4
    assert result.points_written == 7
