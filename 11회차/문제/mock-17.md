<!--meta
번호: 17
대상장: 6
대상절: 6.5
절제목: 대용량 배치 프로그램 튜닝
문제유형: 직접지목형
보조자료: 실행계획
DBMS: 오라클
정답: 2
선택지유형: 서술형
함정유형: [값스왑]
대상개념: [PQ_DISTRIBUTE, 병렬_조인, 데이터_재분배]
자극물밀도: 실행계획_병렬_11행
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 17

### 문제

열수송 누수 분석 야간 배치가 `누수감지이벤트`(약 3억 5천만 건)와 `관로구간`(약 4만 8천 건)을 **관로구간ID로 조인**해 구간별 누수 건수를 집계한다. 한쪽은 대형 팩트, 다른 쪽은 소형 차원 테이블이며, 어느 쪽도 관로구간ID 기준 파티션이 아니다. 아래 병렬 실행계획에서 두 테이블이 병렬 서버(Slave) 사이에 어떤 분배 방식으로 조인되는지 직접 지목한 설명으로 가장 적절한 것은?

#### [아 래]

```text
| Id  | Operation                    | Name          | Pstart| Pstop | TQ    |IN-OUT|
|-----|------------------------------|---------------|-------|-------|-------|------|
|   0 | SELECT STATEMENT             |               |       |       |       |      |
|   1 |  PX COORDINATOR              |               |       |       |       |      |
|   2 |   PX SEND QC (RANDOM)        | :TQ10001      |       |       | Q1,01 | P->S |
|   3 |    HASH GROUP BY             |               |       |       | Q1,01 | PCWP |
|*  4 |     HASH JOIN                |               |       |       | Q1,01 | PCWP |
|   5 |      PX RECEIVE              |               |       |       | Q1,01 | PCWP |
|   6 |       PX SEND BROADCAST      | :TQ10000      |       |       | Q1,00 | P->P |
|   7 |        PX BLOCK ITERATOR     |               |       |       | Q1,00 | PCWC |
|*  8 |         TABLE ACCESS FULL    | 관로구간       |       |       | Q1,00 | PCWP |
|   9 |      PX BLOCK ITERATOR       |               |       |       | Q1,01 | PCWC |
|* 10 |       TABLE ACCESS FULL      | 누수감지이벤트  |       |       | Q1,01 | PCWP |
```

### 선택지

① 조인 키 관로구간ID의 해시로 관로구간(Id 8)과 누수감지이벤트(Id 10)를 양쪽 모두 재분배(hash-hash)한 뒤 각 서버가 자기 버킷 범위의 행만 조인하며, 그 재분배가 Id 6에서 관로구간, Id 9에서 누수감지이벤트에 대해 각각 일어난다.

② 소형 관로구간(Id 8)을 `PX SEND BROADCAST`(Id 6)로 모든 병렬 서버에 복제하고, 대형 누수감지이벤트(Id 10)는 재분배 없이 각 서버가 자기 블록 범위만 읽어(Id 9 `PX BLOCK ITERATOR`) 로컬로 조인하는 broadcast 분배다.

③ 두 테이블이 관로구간ID로 동일하게 파티셔닝돼 있어 재분배 없이 대응 파티션 집합만 로컬로 조인하는 (full) 파티션 와이즈 조인이며, Id 8·Id 10이 같은 PX PARTITION 아래에서 읽힌다.

④ 대형 누수감지이벤트를 `PX SEND BROADCAST`로 전 서버에 복제하고, 소형 관로구간은 각 서버가 자기 블록 범위만 읽어 조인하는 broadcast 분배다.

---

### 정답 — ②

### 왜 ②인가

분배 방식은 **어느 입력이 `PX SEND`를 거치고 그 SEND의 종류가 무엇인지**로 읽습니다. 조인 입력 두 갈래를 나란히 봅니다.

```text
Id 6  PX SEND BROADCAST :TQ10000 (Q1,00 → 전 서버 복제)  관로구간을 모든 서버에 뿌림
Id 8   TABLE ACCESS FULL 관로구간 (약 4.8만 건)            복제 대상 — 소형
Id 9  PX BLOCK ITERATOR (Q1,01 → SEND 없음)               누수감지이벤트를 제자리에서 읽음
Id 10  TABLE ACCESS FULL 누수감지이벤트 (약 3.5억 건)       재분배 안 함 — 대형
```

- 소형 `관로구간`(Id 8) 위에는 `PX SEND BROADCAST`(Id 6)가 있어 각 병렬 서버에 **통째로 복제**됩니다.
- 대형 `누수감지이벤트`(Id 10) 위에는 `PX SEND`가 없습니다. Id 9 `PX BLOCK ITERATOR`로 각 서버가 **자기 블록 범위만** 읽어, 서버마다 들고 있는 관로구간 복제본과 로컬로 조인(Id 4 `HASH JOIN`)합니다.
- 한쪽에만 SEND(그것도 BROADCAST)가 있고 다른 쪽은 SEND 없이 제자리 스캔 — 이 조합이 broadcast 분배입니다. 대형×소형에서는 소형을 복제해도 늘어나는 양이 작고, 대형 3.5억 건을 재분배하는 왕복을 피하므로 유리합니다.

```text
① hash-hash   : 양쪽 위에 각각 PX SEND HASH        → 대형 쪽 Id 9는 SEND 없는 BLOCK ITERATOR   ✗
② broadcast   : 소형에 SEND BROADCAST, 대형은 SEND 없음 → Id 6·Id 8·Id 9·Id 10과 일치            ✔
③ full PWJ    : 두 입력이 같은 PX PARTITION 아래, SEND 없음 → 소형 쪽에 SEND BROADCAST 있음      ✗
④ broadcast(역): 대형을 BROADCAST, 소형을 제자리     → SEND BROADCAST는 소형(Id 8) 쪽에 붙어 있음  ✗
```

SEND가 **소형 관로구간 쪽에만 하나(Id 6 BROADCAST)** 있고 대형 누수감지이벤트 쪽은 SEND 없이 `PX BLOCK ITERATOR`(Id 9)라는 사실이 hash-hash·full PWJ·방향을 뒤집은 broadcast를 한꺼번에 배제합니다. 따라서 ②가 옳습니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ✗ | hash-hash면 양쪽 입력 위에 각각 `PX SEND HASH`가 있어야 하는데, 대형 누수감지이벤트 쪽(Id 9)은 SEND 없는 `PX BLOCK ITERATOR`이고 SEND는 소형 쪽 Id 6의 `BROADCAST` 하나뿐입니다. 분배 방식을 broadcast에서 hash-hash로 뒤바꾼 진술입니다 |
| ② | **○** | 소형 관로구간(Id 8) 위 `PX SEND BROADCAST`(Id 6)로 전 서버에 복제하고, 대형 누수감지이벤트(Id 10)는 SEND 없이 `PX BLOCK ITERATOR`(Id 9)로 제자리 스캔해 로컬 조인하는 broadcast 분배와 일치합니다 |
| ③ | ✗ | full 파티션 와이즈면 두 입력이 같은 `PX PARTITION` 아래에서 SEND 없이 읽혀야 하는데, 소형 쪽에 `PX SEND BROADCAST`(Id 6)가 있고 두 테이블 모두 관로구간ID 기준 파티션도 아닙니다 |
| ④ | ✗ | `PX SEND BROADCAST`(Id 6)는 소형 관로구간(Id 8) 쪽에 붙어 있고, 대형 누수감지이벤트(Id 10)는 Id 9 `PX BLOCK ITERATOR`로 제자리 스캔합니다. 복제되는 테이블을 대형·소형으로 뒤바꾼 값스왑입니다 |

---

## ✅ 이 문제의 핵심

1. **분배 방식은 조인 입력의 `PX SEND` 유무와 종류로 판별**합니다. 여기서는 소형 쪽(Id 6)에만 `PX SEND BROADCAST`가 있고 대형 쪽(Id 9)은 SEND가 없습니다.
2. **broadcast는 대형×소형에서 소형을 전 서버에 복제하고 대형은 제자리에서 읽는 방식**입니다. 각 서버가 소형 복제본과 자기 블록의 대형 행을 로컬 조인합니다.
3. **한쪽에만 SEND(BROADCAST)가 있고 다른 쪽은 SEND 없이 `PX BLOCK ITERATOR`라는 점이 핵심 단서**입니다. 양쪽에 SEND HASH가 있으면 hash-hash, SEND가 아예 없으면 full PWJ입니다.
4. **복제 방향이 중요합니다.** BROADCAST는 소형(Id 8) 쪽에 붙어야 하며, 대형(3.5억)을 복제한다고 보면 방향을 뒤바꾼 값스왑입니다 — 대형을 복제하면 서버 수만큼 불어나 오히려 불리합니다.

📌 한 줄 정리: 소형 관로구간(Id 8) 위에만 `PX SEND BROADCAST`(Id 6)가 있고 대형 누수감지이벤트(Id 10)는 SEND 없이 `PX BLOCK ITERATOR`(Id 9)로 제자리 스캔해 로컬 조인하므로, 소형을 복제하는 broadcast 분배다.
