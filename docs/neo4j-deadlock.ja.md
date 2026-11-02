# Neo4j deadlock への対応

[日本語 README](../README.ja.md) · [한국어版](neo4j-deadlock.md)

当時発生した問題と、本人確認によって解決が確認された範囲を説明します。現在の公開リポジトリには Neo4j 関連の実行コードは含まれていません。
<!-- CLM-028: USER,CODE,RUNTIME,RETROSPECTIVE / CONFIRMED; CLM-029: USER,CODE,RUNTIME,RETROSPECTIVE / CONFIRMED; REC-007: RECONSTRUCTED -->

## 問題

記事ごとに Neo4j へ並列 `MERGE` を実行していた際に、`DeadlockDetected` エラーが発生しました。
<!-- CLM-028: USER,CODE,RUNTIME,RETROSPECTIVE / CONFIRMED -->

## 変更と確認

| 順序 | 確認された内容 |
|---|---|
| エラーの確認 | 記事ごとの並列 `MERGE` で deadlock を経験 |
| 変更 | 記事ごとの write を `UNWIND` による batch upsert に変更し、retry/backoff を適用 |
| 再実行 | 変更を反映して再実行し、該当障害が解決したと本人が確認 |

`UNWIND` は渡されたリストを Cypher で行として扱う機能です。この事例では、記事単位で行っていた write を複数項目を扱う batch upsert に変更しました。retry/backoff は、失敗した処理を再試行する際に試行間隔を置く方法です。当時の再試行回数や間隔は確定していません。
<!-- CLM-029: USER,CODE,RUNTIME,RETROSPECTIVE / CONFIRMED -->

## 現在の観点で理解する

Neo4j では、同時に実行するトランザクションが互いに必要なロックを待つことで deadlock が発生する場合があります。複数項目を batch として渡す方法と、一時的なエラーに対する retry/backoff は、それぞれ write の構造とエラー対応に関わる方法です。

これは**現在の一般的な技術解釈**です。この事例でどのロック競合が発生したか、batch 化と retry のどちらが解決にどの程度寄与したかは確認されていません。`UNWIND` を使用するだけで deadlock がなくなる保証もありません。

参考: [Neo4j の同時アクセスと deadlock](https://neo4j.com/docs/operations-manual/current/database-internals/concurrent-data-access/) · [Cypher `UNWIND`](https://neo4j.com/docs/cypher-manual/5/clauses/unwind/)
<!-- CLM-028, CLM-029: USER,CODE,RUNTIME,RETROSPECTIVE / CONFIRMED; current technical explanation: RECONSTRUCTED -->

## 確認できる範囲

- 保存された元の質問とコードは、エラーの発生と batch への変更依頼を裏づけます。解決は本人による変更・再実行の確認に基づき、成功時の原文ログは確保されていません。
- 同じ session への同時呼び出しが原因だったという仮説は確定していません。
- この事例だけでは、グラフ全体の取り込み範囲、恒久的な再発防止、処理時間の改善は証明できません。
<!-- CLM-028, CLM-029: USER,CODE,RUNTIME,RETROSPECTIVE / CONFIRMED; CLM-059: USER,CODE,RUNTIME,RETROSPECTIVE / PROBABLE -->

## 現在の公開コードとの関係

現在のコードは記事のインデックス作成コアと ES・Qdrant の保存アダプターです。Neo4j の事例は過去の経験を説明するものであり、この機能を現在のリポジトリで実行できることを意味しません。
<!-- REC-001, REC-007: RECONSTRUCTED -->
