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
대상개념: [PQ_DISTRIBUTE, 병렬_조인, Partition_Wise_Join]
자극물밀도: 실행계획_병렬_13행
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 17

### 문제

송전수급 정산 야간 배치가 `급전지시`(약 4억 1천만 건)와 `발전기실적`(약 2억 8천만 건)을 **발전기ID로 조인**해 발전기별 정산금액을 집계한다. 두 테이블 모두 대형이며, 어느 쪽도 발전기ID 기준 파티션이 아니다. 아래 병렬 실행계획에서 두 테이블이 병렬 서버(Slave) 사이에 어떤 분배 방식으로 조인되는지 직접 지목한 설명으로 가장 적절한 것은?

#### [아 래]

```text
| Id  | Operation                 | Name        | Pstart| Pstop | TQ    |IN-OUT|
|-----|---------------------------|-------------|-------|-------|-------|------|
|   0 | SELECT STATEMENT          |             |       |       |       |      |
|   1 |  PX COORDINATOR           |             |       |       |       |      |
|   2 |   PX SEND QC (RANDOM)     | :TQ10002    |       |       | Q1,02 | P->S |
|   3 |    HASH GROUP BY          |             |       |       | Q1,02 | PCWP |
|*  4 |     HASH JOIN BUFFERED    |             |       |       | Q1,02 | PCWP |
|   5 |      PX RECEIVE           |             |       |       | Q1,02 | PCWP |
|   6 |       PX SEND HASH        | :TQ10000    |       |       | Q1,00 | P->P |
|   7 |        PX BLOCK ITERATOR  |             |       |       | Q1,00 | PCWC |
|   8 |         TABLE ACCESS FULL | 급전지시    |       |       | Q1,00 | PCWP |
|   9 |      PX RECEIVE           |             |       |       | Q1,02 | PCWP |
|  10 |       PX SEND HASH        | :TQ10001    |       |       | Q1,01 | P->P |
|  11 |        PX BLOCK ITERATOR  |             |       |       | Q1,01 | PCWC |
|  12 |         TABLE ACCESS FULL | 발전기실적  |       |       | Q1,01 | PCWP |
```

### 선택지

① 소형 쪽을 `PX SEND BROADCAST`로 모든 병렬 서버에 복제하고 대형 쪽은 재분배 없이 각 서버가 자기 블록 범위만 읽어 조인하는 broadcast 분배이며, 그 복제가 Id 6에서 일어난다.

② 조인 키 발전기ID의 해시로 급전지시(Id 8)와 발전기실적(Id 12)을 **양쪽 모두 재분배(hash-hash)** 한 뒤 각 서버가 자기 버킷 범위의 행만 조인하며, 그 재분배가 Id 6·Id 10의 `PX SEND HASH`에서 각각 일어난다.

③ 두 테이블이 발전기ID로 동일하게 파티셔닝돼 있어 재분배 없이 대응 파티션 집합만 로컬로 조인하는 (full) 파티션 와이즈 조인이며, Id 8·Id 12가 같은 PX PARTITION 아래에서 읽힌다.

④ 대형 급전지시만 파티션 단위로 각 서버가 읽고, 발전기실적을 급전지시의 파티션 경계에 맞춰 `PX SEND PARTITION (KEY)`로 재분배하는 부분(partial) 파티션 와이즈 조인이다.

---

### 정답 — ②

### 왜 ②인가

분배 방식은 **어느 입력이 `PX SEND`를 거치고 그 SEND의 종류가 무엇인지**로 읽습니다.

```text
Id 6  PX SEND HASH :TQ10000 (Q1,00 → 해시 재분배)   급전지시를 발전기ID 해시로 뿌림
Id 8   TABLE ACCESS FULL 급전지시 (약 4.1억 건)       재분배 대상 — 대형
Id 10 PX SEND HASH :TQ10001 (Q1,01 → 해시 재분배)   발전기실적을 발전기ID 해시로 뿌림
Id 12  TABLE ACCESS FULL 발전기실적 (약 2.8억 건)      재분배 대상 — 대형
```

- 조인 입력 **양쪽 모두** 위에 `PX SEND HASH`가 있습니다. 급전지시는 Id 6, 발전기실적은 Id 10에서 각각 조인 키 발전기ID의 해시로 재분배됩니다.
- 두 입력이 같은 해시 함수로 뿌려지므로, 같은 발전기ID는 같은 서버로 모입니다. 각 서버는 **자기 버킷 범위의 행만** 받아 로컬로 조인(Id 4 `HASH JOIN BUFFERED`)합니다.
- 이 조합이 hash-hash 분배입니다. 두 테이블이 모두 대형(4.1억·2.8억)이라 한쪽을 복제(broadcast)하면 그 큰 집합이 서버 수만큼 불어나므로, 양쪽을 해시로 갈라 나눠 갖는 편이 유리합니다.

```text
① broadcast    : 한쪽에 PX SEND BROADCAST, 다른 쪽 SEND 없음   → 양쪽 다 PX SEND HASH   ✗
② hash-hash    : 양쪽 위에 각각 PX SEND HASH                    → Id 6·Id 10과 일치        ✔
③ full PWJ     : 두 입력이 같은 PX PARTITION 아래, SEND 없음    → 양쪽에 SEND HASH 있음   ✗
④ partial PWJ  : 한쪽에 PX SEND PARTITION (KEY)                 → SEND 종류가 HASH        ✗
```

양쪽 입력에 `PX SEND HASH`가 하나씩(Id 6·Id 10) 있다는 사실이 broadcast·full PWJ·partial PWJ를 한꺼번에 배제합니다. 따라서 ②가 옳습니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ✗ | broadcast면 한쪽에 `PX SEND BROADCAST`가 있고 다른 쪽은 SEND가 없어야 하는데, 이 플랜은 Id 6·Id 10 양쪽 모두 `PX SEND HASH`입니다. 분배 방식을 hash-hash에서 broadcast로 뒤바꾼 진술입니다 |
| ② | **○** | 조인 입력 양쪽(Id 8·Id 12) 위에 각각 `PX SEND HASH`(Id 6·Id 10)가 있어 발전기ID 해시로 양쪽을 재분배하고, 각 서버가 자기 버킷 범위만 로컬 조인하는 hash-hash 분배와 일치합니다 |
| ③ | ✗ | full 파티션 와이즈면 두 입력이 같은 `PX PARTITION` 아래에서 SEND 없이 읽혀야 하는데, 양쪽이 `PX SEND HASH`(Id 6·Id 10)로 재분배되고 있고 두 테이블 모두 발전기ID 기준 파티션도 아닙니다 — hash-hash를 PWJ로 뒤바꾼 값스왑입니다 |
| ④ | ✗ | partial 파티션 와이즈면 재분배되는 쪽에 `PX SEND PARTITION (KEY)`가 있어야 하는데, Id 6·Id 10의 SEND는 둘 다 `HASH`입니다. SEND 종류를 HASH에서 PARTITION (KEY)로 뒤바꾼 진술입니다 |

---

## ✅ 이 문제의 핵심

1. **분배 방식은 조인 입력의 `PX SEND` 종류로 판별**합니다. 여기서는 양쪽 입력에 `PX SEND HASH`(Id 6·Id 10)가 하나씩 있습니다.
2. **hash-hash는 대형×대형에서 양쪽을 조인 키 해시로 나눠 갖는 방식**입니다. 같은 발전기ID가 같은 서버로 모여 각 서버가 자기 버킷만 조인합니다.
3. **양쪽 모두 SEND HASH라는 점이 핵심 단서**입니다. 한쪽만 SEND가 있으면 broadcast, SEND가 아예 없으면 full PWJ입니다.
4. **broadcast·full PWJ·partial PWJ는 각각 `PX SEND BROADCAST`·같은 PX PARTITION 아래·`PX SEND PARTITION (KEY)`가 있어야** 성립합니다. 이 플랜의 SEND는 양쪽 HASH뿐이라 셋 다 배제됩니다 — 분배 방식을 뒤바꾼 값스왑 오답입니다.

📌 한 줄 정리: 조인 입력 양쪽(Id 8·Id 12) 위에 각각 `PX SEND HASH`(Id 6·Id 10)가 있어 발전기ID 해시로 두 대형 테이블을 모두 재분배하고 각 서버가 자기 버킷만 로컬 조인하므로, hash-hash 분배다.
