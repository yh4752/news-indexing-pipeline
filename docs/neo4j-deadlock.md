# Neo4j deadlock 대응

[한국어 README](../README.md) · [日本語版](neo4j-deadlock.ja.md)

이 문서는 **당시 발생한 문제와 사용자 확인으로 해결된 범위**를 설명합니다. 현재 공개 저장소에는 Neo4j 관련 실행 코드가 포함되어 있지 않습니다.
<!-- CLM-028: USER,CODE,RUNTIME,RETROSPECTIVE / CONFIRMED; CLM-029: USER,CODE,RUNTIME,RETROSPECTIVE / CONFIRMED; REC-007: RECONSTRUCTED -->

## 문제

기사별로 Neo4j에 병렬 `MERGE`를 수행하던 중 `DeadlockDetected` 오류가 발생했습니다.
<!-- CLM-028: USER,CODE,RUNTIME,RETROSPECTIVE / CONFIRMED -->

## 변경과 확인

| 순서 | 확인된 내용 |
|---|---|
| 오류 확인 | 기사별 병렬 `MERGE` 과정에서 deadlock 오류를 경험 |
| 변경 | 기사별 write를 `UNWIND`를 이용한 batch upsert로 변경하고 retry/backoff 적용 |
| 재실행 | 변경을 반영하고 다시 실행해 해당 장애를 해결했다고 사용자가 확인 |

`UNWIND`는 전달한 목록을 Cypher에서 행 단위로 다루는 기능입니다. 이 사례에서는 기사 단위로 수행하던 write를 여러 항목을 다루는 batch upsert 형태로 변경했습니다. retry/backoff는 실패한 작업을 재시도할 때 재시도 간 기다리는 방식입니다. 당시 재시도 횟수나 간격은 확정하지 않습니다.
<!-- CLM-029: USER,CODE,RUNTIME,RETROSPECTIVE / CONFIRMED -->

## 현재 관점에서 이해하기

Neo4j에서는 동시 트랜잭션이 서로 필요한 락을 기다리면 deadlock이 발생할 수 있습니다. 여러 항목을 batch로 전달하는 방식과 일시적 오류에 대한 retry/backoff는 각각 write 구조와 오류 대응을 다루는 방법입니다.

이 설명은 **현재의 일반적인 기술 해석**입니다. 이 사례에서 정확히 어떤 락 경합이 발생했는지, batch 전환과 retry 중 어느 요소가 해결에 얼마나 기여했는지는 확인되지 않았습니다. `UNWIND`만 사용하면 deadlock이 사라진다고 보장하지도 않습니다.

참고: [Neo4j의 동시 접근과 deadlock](https://neo4j.com/docs/operations-manual/current/database-internals/concurrent-data-access/) · [Cypher `UNWIND`](https://neo4j.com/docs/cypher-manual/5/clauses/unwind/)
<!-- CLM-028, CLM-029: USER,CODE,RUNTIME,RETROSPECTIVE / CONFIRMED; current technical explanation: RECONSTRUCTED -->

## 확인 범위

- 보존된 원래 질문·코드는 오류 발생과 batch 전환 요청을 보강합니다. 해결은 사용자의 적용·재실행 확인에 근거하며, 원문 성공 로그는 확보되지 않았습니다.
- 같은 session의 동시 호출이 원인이었다는 가설을 확정하지 않습니다.
- 이 사례만으로 전체 그래프 적재 범위, 영구 무재발 또는 처리 시간 개선을 증명하지 않습니다.
<!-- CLM-028, CLM-029: USER,CODE,RUNTIME,RETROSPECTIVE / CONFIRMED; CLM-059: USER,CODE,RUNTIME,RETROSPECTIVE / PROBABLE -->

## 현재 공개 코드와의 관계

현재 저장소의 코드는 기사 인덱싱 코어와 ES·Qdrant 저장 어댑터입니다. Neo4j 사례는 과거 경험을 설명하는 자료이며 해당 기능이 이 저장소에서 실행된다는 뜻이 아닙니다.
<!-- REC-001, REC-007: RECONSTRUCTED -->
