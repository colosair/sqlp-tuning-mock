<!--meta
번호: 15
대상장: 6
대상절: 6.2
절제목: DML 튜닝
문제유형: 적절하지_않은_것
보조자료: SQL
DBMS: 오라클
정답: 4
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

전략 석유비축 관리의 야간 배치가 하루치 유류 입출고(약 8,000만 행)를 수집 테이블에서 `비축유입출고`(약 12억 행)로 대량 적재한다. 적재 시간을 줄이려고 아래처럼 `APPEND` 힌트와 병렬 DML을 적용했다. `비축유입출고` 세그먼트는 NOLOGGING이고 DB는 force logging이 아니며, 이 테이블에는 비유니크 인덱스 3개가 걸려 있다. 이 대량 DML 튜닝에 대한 설명으로 가장 적절하지 <u>않은</u> 것은?

#### [아 래]

```sql
-- 일일 유류 입출고를 비축유입출고에 대량 적재하는 야간 배치
ALTER SESSION ENABLE PARALLEL DML;

INSERT /*+ APPEND PARALLEL(t, 4) */ INTO 비축유입출고 t
SELECT * FROM 입출고_수집;

COMMIT;
```

### 선택지

① `INSERT /*+ APPEND */` 는 Direct Path Insert로 동작해, HWM 위쪽 새 블록에 데이터를 기록하고 버퍼 캐시와 freelist 탐색을 우회하므로 대량 적재 속도가 빨라진다.

② 세그먼트가 NOLOGGING이고 DB가 force logging이 아니어야 Direct Path Insert가 데이터에 대한 redo를 최소화한다 — 이 조건이 아니면 direct path여도 redo가 정상적으로 쌓이고, 일반(conventional) 인서트에는 nologging이 redo 절감 효과를 주지 못한다.

③ `ALTER SESSION ENABLE PARALLEL DML` 후 병렬 INSERT를 수행하면 여러 PX 서버가 각자 자기 익스텐트에 direct path로 적재하며, 이때 대상 테이블은 배타 모드로 잠겨 커밋 전까지 같은 테이블에 대한 다른 DML은 대기한다.

④ Direct Path Insert도 인덱스는 일반 인서트처럼 행을 넣을 때마다 즉시 리프에 반영하므로, 적재 전에 인덱스를 unusable로 돌렸다가 적재 후 재생성하는 방식은 대량 적재에서 이득이 없다.

---

### 정답 — ④

### 왜 ④인가

Direct Path Insert의 인덱스 유지 방식은 일반 인서트와 다릅니다. 일반(conventional) 인서트는 행을 넣을 때마다 인덱스 리프를 그때그때 갱신하지만, direct path는 적재분에 대한 인덱스 엔트리를 **임시 세그먼트에 따로 모아 두었다가 적재 종료 시점에 기존 인덱스와 한 번에 병합(merge)** 합니다.

```text
[ 인덱스 유지 방식 비교 ]
일반 인서트      : 행 1건 → 인덱스 3개 리프에 즉시 반영 (건별 × 인덱스 수)
Direct Path      : 적재분 인덱스 엔트리를 임시 세그먼트에 축적 → 종료 시 일괄 병합
대량 + 다중 인덱스 : unusable 후 적재 → 인덱스 rebuild 가 병합 비용보다 유리한 경우가 많음
```

④는 두 군데를 뒤집었습니다. 첫째, direct path가 인덱스를 "행별로 즉시 반영"한다고 했으나 실제로는 일괄 병합 방식입니다. 둘째, 그래서 "unusable 후 재생성이 이득이 없다"고 했으나, 인덱스가 여럿이고 적재량이 클수록 인덱스를 미리 unusable로 두고 적재한 뒤 rebuild 하는 편이 병합 부하를 피해 더 빠른 경우가 많습니다. ④는 인덱스 유지 메커니즘과 그에 따른 튜닝 방향을 **정반대**로 서술했으므로 부적절합니다.

①은 direct path의 HWM 위 적재·버퍼 캐시 우회를, ②는 nologging이 direct path에서만 redo를 줄인다는 전제 조건을, ③은 병렬 DML의 PX별 적재와 테이블 배타 잠금을 옳게 서술합니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ○ | APPEND는 direct path로 HWM 위 새 블록에 기록하고 버퍼 캐시·freelist를 우회하므로 대량 적재가 빨라집니다 |
| ② | ○ | nologging + non-force-logging이라야 direct path의 데이터 redo가 최소화되며, 일반 인서트에는 nologging이 redo 절감 효과가 없습니다 |
| ③ | ○ | 병렬 DML을 켜면 PX 서버가 각자 익스텐트에 direct path로 적재하고, 대상 테이블은 배타 모드로 잠겨 커밋 전까지 다른 DML이 대기합니다 |
| ④ | **✗** | direct path는 인덱스 엔트리를 임시 세그먼트에 모아 종료 시 일괄 병합합니다. 다중 인덱스·대량 적재에선 unusable 후 rebuild가 유리한 경우가 많아 "이득 없음"은 반대입니다 |

---

## ✅ 이 문제의 핵심

1. **Direct Path Insert는 HWM 위 새 블록에 적재**합니다. 버퍼 캐시와 freelist 탐색을 우회해 대량 적재를 가속합니다.
2. **nologging은 direct path에서만 효과**입니다. 세그먼트 NOLOGGING + DB non-force-logging 조건에서 데이터 redo가 최소화되며, 일반 인서트에는 무의미합니다.
3. **병렬 DML은 테이블을 배타 잠금**합니다. PX 서버가 각자 익스텐트에 적재하고, 커밋 전까지 같은 테이블의 다른 DML은 대기합니다.
4. **인덱스는 일괄 병합 방식**입니다. 행별 즉시 반영이 아니라 임시 세그먼트 축적 후 병합이라, 다중 인덱스·대량 적재에선 unusable 후 rebuild가 흔히 더 빠릅니다.

📌 한 줄 정리: Direct Path Insert의 인덱스는 임시 세그먼트에 모았다가 일괄 병합하며 대량·다중 인덱스에선 unusable 후 rebuild가 유리한데, ④는 "행별 즉시 반영이라 재생성이 이득 없다"고 정반대로 서술해 부적절합니다.
