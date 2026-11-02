import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from news_rag_reconstruction.models import Article


@pytest.fixture
def fixture_articles() -> tuple[Article, ...]:
    fixture_path = Path(__file__).parent / "fixtures" / "articles.json"
    records: list[dict[str, Any]] = json.loads(fixture_path.read_text(encoding="utf-8"))

    return tuple(
        Article(
            article_id=record["article_id"],
            title=record["title"],
            content=record["content"],
            organization=record["organization"],
            published_at=(
                datetime.fromisoformat(record["published_at"])
                if record["published_at"] is not None
                else None
            ),
        )
        for record in records
    )
