<!--meta
번호: 15
대상장: 6
대상절: 6.2
절제목: DML 튜닝
문제유형: 적절한_것
보조자료: SQL
DBMS: 오라클
정답: 1
선택지유형: 서술형
함정유형: [경계_오해]
대상개념: [Direct_Path_Insert, 병렬_DML, minimal_logging]
자극물밀도: SQL
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 15

### 문제

관세청 통관시스템의 `수입신고`(약 8억 건)는 신고일자 기준 일별 RANGE 파티션 테이블이다. 야간 배치는 당일 신고분(약 400만 건)을 **비파티션 임시 테이블 `수입신고_당일`에 대량 적재**한 뒤, 이를 대상 파티션과 **교환(EXCHANGE PARTITION)** 하는 방식으로 반영한다(아래 DDL·DML). 두 테이블 모두 `NOLOGGING` 속성이며, 데이터베이스는 FORCE LOGGING이 아니다. 이 대량 적재·교환 방식에 대한 설명으로 가장 적절한 것은?

#### [아 래]

```sql
-- 임시 테이블(비파티션) : 대상 파티션과 구조·칼럼 동일, NOLOGGING
CREATE TABLE 수입신고_당일 ( ... ) NOLOGGING;

-- ① 당일분 대량 적재 (Direct Path + 병렬)
ALTER SESSION ENABLE PARALLEL DML;
INSERT /*+ APPEND PARALLEL(t, 4) */ INTO 수입신고_당일 t
SELECT * FROM 외부신고_수신 s;
COMMIT;

-- ② 로컬 인덱스 생성 후 대상 파티션과 교환
ALTER TABLE 수입신고
  EXCHANGE PARTITION p_20260718 WITH TABLE 수입신고_당일
  INCLUDING INDEXES WITHOUT VALIDATION;
```

### 선택지

① `INSERT /*+ APPEND */`는 세그먼트 HWM 위에 새 블록을 직접 기록하는 Direct Path 적재이고, 대상 테이블이 NOLOGGING이며 FORCE LOGGING도 아니므로 이 적재의 데이터 리두가 최소화(minimal logging)된다. 이후 EXCHANGE PARTITION은 데이터를 물리 이동하지 않고 딕셔너리에서 세그먼트를 맞바꾸는 메타데이터 연산이라 대용량이라도 순식간에 끝난다.

② 병렬 DML은 `PARALLEL` 힌트만 주면 세션 설정과 무관하게 INSERT 부분이 병렬로 수행되므로, `ALTER SESSION ENABLE PARALLEL DML` 문장은 실제 병렬 적재에 영향을 주지 않는 관례적 선언에 불과하다.

③ Direct Path 적재가 진행되는 동안에도 다른 세션은 `수입신고_당일`에 자유롭게 일반 INSERT/UPDATE를 수행할 수 있으며, 적재 세션은 커밋 전까지 그 테이블에 배타적 잠금을 걸지 않는다.

④ EXCHANGE PARTITION에 `WITHOUT VALIDATION`을 주면 검증 비용을 없애는 동시에, 임시 테이블에 대상 파티션 범위를 벗어난 행이 섞여 있어도 오라클이 교환 시점에 이를 안전하게 걸러 올바른 파티션으로 자동 재배치한다.

---

### 정답 — ①

### 왜 ①인가

이 배치는 대량 적재의 3대 무기 — **Direct Path Insert(APPEND) · 병렬 DML · minimal logging** — 를 EXCHANGE PARTITION과 결합한 정석입니다. 각 무기의 **작동 경계**를 정확히 짚어야 옳은 진술을 가릴 수 있습니다.

```text
[ 각 단계의 실제 동작 ]
INSERT /*+ APPEND */  → HWM 위 새 블록에 직접 기록(버퍼캐시 우회, Direct Path)
   + 대상 NOLOGGING + DB가 FORCE LOGGING 아님 → 데이터 리두 최소화(minimal logging)
PARALLEL(t,4)         → SELECT뿐 아니라 INSERT까지 병렬로 하려면
   ENABLE PARALLEL DML 선행 필수 (없으면 INSERT는 직렬)
EXCHANGE PARTITION    → 세그먼트 포인터만 맞바꾸는 딕셔너리 연산 → 데이터 이동 없음
```

①은 세 가지를 모두 정확히 서술합니다. APPEND는 HWM 위 직접 기록(Direct Path)이고, NOLOGGING + 비FORCE LOGGING 조건이 갖춰지면 데이터 리두가 minimal logging으로 줄며, EXCHANGE PARTITION은 세그먼트를 맞바꾸는 메타데이터 연산이라 800만이든 8억이든 데이터를 옮기지 않아 즉시 끝납니다. 경계 조건(NOLOGGING이되 FORCE LOGGING이 아닐 것)까지 발문과 일치하므로 옳은 진술은 ①입니다.

②③④는 각 기능의 동작 경계를 뭉갠 **경계 오해**입니다(아래 표).

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | **○** | APPEND는 HWM 위 Direct Path 기록이고, NOLOGGING+비FORCE LOGGING이면 데이터 리두가 최소화되며, EXCHANGE는 세그먼트를 맞바꾸는 메타데이터 연산이라 즉시 끝납니다 |
| ② | ✗ | 힌트만으로는 SELECT만 병렬이 되고 INSERT는 직렬입니다. INSERT까지 병렬 DML로 돌리려면 `ENABLE PARALLEL DML` 선언이 반드시 선행돼야 합니다 — 이 문장은 필수입니다 |
| ③ | ✗ | Direct Path 적재는 대상 테이블에 배타적 테이블 잠금을 걸어, 커밋 전까지 다른 세션의 일반 DML을 막습니다. 자유로운 동시 DML은 불가능합니다 |
| ④ | ✗ | `WITHOUT VALIDATION`은 범위 검증을 생략할 뿐 자동 재배치가 아닙니다. 범위를 벗어난 행이 섞이면 그대로 파티션에 들어가 프루닝·조회가 어긋납니다 |

---

## ✅ 이 문제의 핵심

1. **Direct Path Insert(APPEND)** 는 HWM 위 새 블록에 직접 기록하며, 그동안 대상 테이블에 배타적 잠금을 걸어 동시 DML을 막습니다.
2. **minimal logging의 경계**: 객체가 NOLOGGING이고 DB가 FORCE LOGGING이 아니며 Direct Path일 때만 데이터 리두가 최소화됩니다 — 세 조건이 함께여야 합니다.
3. **병렬 DML의 경계**: `PARALLEL` 힌트만으로는 SELECT만 병렬입니다. INSERT까지 병렬로 하려면 `ENABLE PARALLEL DML`을 먼저 켜야 합니다.
4. **EXCHANGE PARTITION**은 세그먼트를 맞바꾸는 메타데이터 연산이라 데이터를 옮기지 않습니다. 단 `WITHOUT VALIDATION`은 검증을 생략할 뿐 잘못된 범위 행을 교정해 주지 않습니다.

📌 한 줄 정리: APPEND Direct Path + NOLOGGING(비FORCE LOGGING) + 세그먼트를 맞바꾸는 EXCHANGE PARTITION의 경계를 모두 옳게 짚은 ①이 적절하며, 병렬 DML 활성화·Direct Path 잠금·WITHOUT VALIDATION 검증은 각각 경계를 뭉갠 오답입니다.
