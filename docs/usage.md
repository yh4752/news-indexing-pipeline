# 실행 안내 / 実行ガイド

[한국어 README](../README.md) · [日本語 README](../README.ja.md)

## 설치와 테스트 / セットアップとテスト

Python 3.11 이상과 [uv](https://docs.astral.sh/uv/)가 필요합니다. 최초 의존성 설치에 네트워크가 필요할 수 있습니다. 테스트는 외부 Elasticsearch·Qdrant 서버와 API 키 없이 실행됩니다.

Python 3.11 以上と [uv](https://docs.astral.sh/uv/) が必要です。初回の依存関係インストールにはネットワークが必要な場合があります。テストには外部の Elasticsearch・Qdrant サーバーや API キーは不要です。

```bash
uv sync --locked --dev
uv run --no-sync pytest
uv run --no-sync ruff check src tests
uv run --no-sync ruff format --check src tests
uv run --no-sync mypy src tests
```

## Example

가상 기사 본문을 청크로 나누고 테스트용 벡터의 차원을 출력합니다. ES·Qdrant 저장이나 검색을 실행하지 않습니다.

架空の記事本文をチャンクに分割し、テスト用ベクトルの次元を表示します。ES・Qdrant への保存や検索は実行しません。

```bash
uv run --no-sync python - <<'PY'
from uuid import NAMESPACE_URL

from news_rag_reconstruction.chunking import CharacterChunker
from news_rag_reconstruction.embeddings import FixtureEmbeddingProvider
from news_rag_reconstruction.models import Article
from news_rag_reconstruction.pipeline import V1IndexingPipeline
from news_rag_reconstruction.point_ids import UUID5PointIdStrategy

pipeline = V1IndexingPipeline(
    chunker=CharacterChunker(chunk_size=14, chunk_overlap=4),
    embedding_provider=FixtureEmbeddingProvider(dimension=3),
    point_id_strategy=UUID5PointIdStrategy(namespace=NAMESPACE_URL),
)
examples = (
    ("KO", "입력 기사", "본문", "가상 도서관 야간 운영 연장", "도서관이 야간 열람 시간을 두 시간 연장한다."),
    ("JA", "入力記事", "本文", "図書館の夜間利用を延長", "市立図書館が夜間の開館時間を二時間延長した。"),
)
for language, article_label, content_label, title, content in examples:
    article = Article("news-001", title, content, None, None)
    print(f"[{language}]")
    print(f"{article_label}: {article.article_id} | {article.title}")
    print(f"{content_label}: {article.content}\n")
    for point in pipeline.build_points(article):
        print(
            f"chunk[{point.payload.chunk_index}] article_id={point.payload.article_id} "
            f'text="{point.payload.text}" vector_dim={len(point.vector.values)}'
        )
    print()
PY
```

```text
[KO]
입력 기사: news-001 | 가상 도서관 야간 운영 연장
본문: 도서관이 야간 열람 시간을 두 시간 연장한다.

chunk[0] article_id=news-001 text="도서관이 야간 열람 시간을" vector_dim=3
chunk[1] article_id=news-001 text=" 시간을 두 시간 연장한다" vector_dim=3
chunk[2] article_id=news-001 text="연장한다." vector_dim=3

[JA]
入力記事: news-001 | 図書館の夜間利用を延長
本文: 市立図書館が夜間の開館時間を二時間延長した。

chunk[0] article_id=news-001 text="市立図書館が夜間の開館時間を" vector_dim=3
chunk[1] article_id=news-001 text="館時間を二時間延長した。" vector_dim=3
```

차원·청크 크기·겹침·namespace는 예제용입니다. fixture 벡터는 의미 검색 모델이 아닙니다.

次元・チャンクサイズ・オーバーラップ・namespace は例示用です。fixture ベクトルは意味検索用モデルではありません。
