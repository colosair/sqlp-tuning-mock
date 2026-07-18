<!--meta
번호: 15
대상장: 6
대상절: 6.2
절제목: DML 튜닝
문제유형: 적절하지_않은_것
보조자료: SQL
DBMS: 오라클
정답: 3
선택지유형: 혼합
함정유형: [정반대_진술]
대상개념: [Direct_Path_Insert, nologging, 병렬_DML]
자극물밀도: SQL
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 15

### 문제

산림 생육조사 시스템의 야간 배치가 그날 수집한 임분(林分) 생육 측정치 약 6,000만 건을 스테이징(`생육조사_적재`)에서 조사일자 RANGE 파티션 테이블(`생육조사이력`)로 옮기고, 재적재 대상인 지난 분기 파티션은 통째로 비운다. 아래는 이 배치가 쓰는 DML이다. 대량 적재·삭제 튜닝에 대한 설명으로 가장 적절하지 <u>않은</u> 것은?

#### [아 래]

```sql
ALTER SESSION ENABLE PARALLEL DML;

INSERT /*+ APPEND PARALLEL(t 4) */ INTO 생육조사이력 t
SELECT * FROM 생육조사_적재;

-- 지난 분기 재적재분은 파티션 단위로 비운다
ALTER TABLE 생육조사이력 TRUNCATE PARTITION p_2026q2;
```

### 선택지

① `INSERT /*+ APPEND */`는 Direct Path Insert로 동작해, 세그먼트 HWM 위에 새 블록을 직접 포맷해 써 넣고 버퍼 캐시를 우회하므로 대량 적재에서 재사용 블록 탐색·버퍼 경합을 줄인다.

② 대상 테이블이나 세션이 nologging이면 Direct Path Insert로 적재되는 데이터는 redo를 최소화(minimal logging)할 수 있어 로그 부하가 줄지만, 그 대신 미디어 복구가 필요할 때 해당 데이터를 복구하지 못할 위험이 생긴다.

③ `ALTER TABLE … TRUNCATE PARTITION`은 파티션의 행을 한 건씩 지우며 각 행마다 Undo·Redo를 남기는 DML이라, DELETE보다 Undo 생성이 많고 도중에 ROLLBACK으로 되돌릴 수 있다.

④ 병렬 DML은 `ALTER SESSION ENABLE PARALLEL DML`로 활성화해야 실제 병렬로 수행되며, 병렬 DML로 변경한 테이블은 같은 트랜잭션 안에서 다시 조회·변경할 수 없어 커밋 뒤에 접근해야 한다.

---

### 정답 — ③

### 왜 ③인가

`TRUNCATE PARTITION`은 행 단위로 지우는 DML이 아니라, 파티션 세그먼트의 저장 영역을 통째로 해제하고 HWM을 리셋하는 **DDL**입니다. DDL이므로 행별 Undo를 쌓지 않고, 실행 시점에 **암묵적으로 커밋**되어 트랜잭션의 일부로 ROLLBACK되지 않습니다.

```text
DELETE FROM … WHERE (행 단위)        : DML · 행마다 Undo·Redo 다량 · ROLLBACK 가능 · HWM 유지
TRUNCATE PARTITION (세그먼트 단위)   : DDL · 저장영역 해제·HWM 리셋 · 암묵적 COMMIT · ROLLBACK 불가
                                       ⇒ 대량 삭제에서 Undo·Redo가 훨씬 적고 빠르다
```

③은 두 성질을 **정반대로** 뒤집었습니다. 첫째, TRUNCATE는 "행을 한 건씩 지우며 행마다 Undo를 남기는" 방식이 아니라 세그먼트를 통째로 비우므로 Undo가 **DELETE보다 훨씬 적습니다.** 둘째, TRUNCATE는 DDL이라 암묵적 커밋되어 **ROLLBACK으로 되돌릴 수 없습니다.** ③은 "행 단위·Undo 다량·롤백 가능"이라고 서술해 방향과 되돌림 가능성을 모두 반대로 말했으므로, 부적절한 것은 ③입니다.

①②④는 각각 APPEND의 Direct Path Insert 동작(①), nologging + Direct Path의 최소 로깅과 복구 위험(②), 병렬 DML의 활성화 요건과 같은 트랜잭션 내 재접근 제약(④)을 옳게 서술합니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ○ | APPEND는 Direct Path Insert로 HWM 위에 새 블록을 포맷해 써 넣고 버퍼 캐시를 우회하므로, 재사용 블록 탐색과 버퍼 경합을 줄여 대량 적재에 유리합니다 |
| ② | ○ | nologging + Direct Path Insert는 redo를 최소화해 로그 부하를 줄이지만, 그 데이터는 미디어 복구 대상에서 빠져 복구 불가 위험을 안습니다 |
| ③ | **✗** | TRUNCATE PARTITION은 세그먼트를 통째로 비우는 DDL이라 Undo가 DELETE보다 적고 암묵적 커밋되어 ROLLBACK되지 않습니다 — 방향·되돌림이 반대입니다 |
| ④ | ○ | 병렬 DML은 세션 활성화가 전제이며, 변경한 테이블은 같은 트랜잭션 안에서 재조회·재변경할 수 없어 커밋 뒤에 접근해야 합니다 |

---

## ✅ 이 문제의 핵심

1. **APPEND는 Direct Path Insert**입니다. HWM 위에 새 블록을 직접 써 넣고 버퍼 캐시를 우회해 대량 적재의 재사용 블록 탐색·버퍼 경합을 없앱니다.
2. **nologging + Direct Path는 redo 최소화**입니다. 로그 부하는 줄지만 미디어 복구에서 그 데이터가 빠지는 위험을 감수해야 합니다.
3. **TRUNCATE PARTITION은 DDL**입니다. 세그먼트를 통째로 해제해 Undo·Redo가 DELETE보다 훨씬 적고, 암묵적 커밋되어 ROLLBACK되지 않습니다.
4. **병렬 DML은 세션 활성화가 전제**이며, 변경한 객체는 같은 트랜잭션 안에서 다시 접근할 수 없어 커밋 뒤에 읽어야 합니다.

📌 한 줄 정리: TRUNCATE PARTITION은 세그먼트를 통째로 비우는 DDL이라 Undo가 적고 롤백되지 않는데, ③은 "행 단위로 Undo 남기며 롤백 가능"이라 정반대로 서술해 부적절합니다.
