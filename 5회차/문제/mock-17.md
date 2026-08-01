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
자극물밀도: 실행계획_병렬_10행+
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 17

### 문제

화물추적 배치에서 운송기록 테이블(약 1억 9천만 건)과 검수내역 테이블(약 7,200만 건)을 운송장번호로 병렬 해시 조인한다. 운송기록은 운송장번호 기준 **해시 16 파티션**으로 나뉘어 있으나, 검수내역은 파티셔닝돼 있지 않다. 이 병렬 실행계획은 두 테이블을 병렬 서버(Slave) 사이에 **어떻게 분배**해 조인하는가? 가장 정확히 지목한 것은?

#### [아 래]

```text
| Id  | Operation                    | Name       | Pstart| Pstop | TQ    |IN-OUT|
|-----|------------------------------|------------|-------|-------|-------|------|
|   0 | SELECT STATEMENT             |            |       |       |       |      |
|   1 |  PX COORDINATOR              |            |       |       |       |      |
|   2 |   PX SEND QC (RANDOM)        | :TQ10001   |       |       | Q1,01 | P->S |
|*  3 |    HASH JOIN                 |            |       |       | Q1,01 | PCWP |
|   4 |     PX PARTITION HASH ALL    |            |     1 |    16 | Q1,01 | PCWC |
|   5 |      TABLE ACCESS FULL       | 운송기록    |     1 |    16 | Q1,01 | PCWP |
|   6 |     PX RECEIVE               |            |       |       | Q1,01 | PCWP |
|   7 |      PX SEND PARTITION (KEY) | :TQ10000   |       |       | Q1,00 | P->P |
|   8 |       PX BLOCK ITERATOR      |            |       |       | Q1,00 | PCWC |
|   9 |        TABLE ACCESS FULL     | 검수내역    |       |       | Q1,00 | PCWP |
```

### 선택지

① 운송기록과 검수내역이 둘 다 운송장번호로 해시 파티셔닝돼 있어, Id 4 `PX PARTITION HASH ALL`(Pstart 1~Pstop 16)이 대응 파티션 쌍을 한 서버에 모아 준다. Id 3 HASH JOIN은 재분배 없이 쌍만 조인하는 (full) 파티션 와이즈 조인이고, Id 7 :TQ10000은 결과를 QC로 넘기는 통로다.

② 운송기록은 파티션 단위로 각 서버가 자기 파티션을 재분배 없이 읽고(Id 4 PX PARTITION HASH ALL), 검수내역만 Id 7 `PX SEND PARTITION (KEY)`로 운송기록의 파티션 경계에 맞춰 재분배하는 부분(partial) 파티션 와이즈 조인이다.

③ Id 7의 :TQ10000과 Id 2의 :TQ10001 두 테이블 큐를 거쳐 운송기록과 검수내역을 양쪽 다 운송장번호 해시로 재분배하는 hash-hash 분배이며, Id 5·Id 9 위에 각각 `PX SEND HASH`가 놓여 두 스트림을 Q1,00·Q1,01의 새 해시 버킷으로 흩은 뒤 Id 3 HASH JOIN이 받아 조인한다.

④ 검수내역은 Id 8 `PX BLOCK ITERATOR`로 각 서버가 자기 블록 범위를 재분배 없이 읽고, 파티셔닝된 운송기록만 Id 7 `PX SEND PARTITION (KEY)`로 검수내역이 흩어진 경계에 맞춰 Q1,00에서 Q1,01로 재분배하는 부분(partial) 파티션 와이즈 조인이다.

---

### 정답 — ②

### 왜 ②인가

분배 방식은 **조인(Id 3)의 두 입력이 각각 어떤 경로로 조인 서버 집합에 도달하는지**로 읽습니다.

```text
Id 4  PX PARTITION HASH ALL (Q1,01, Pstart 1~Pstop 16)   운송기록: 파티션 단위 로컬 읽기, 재분배 없음
Id 5  TABLE ACCESS FULL 운송기록 (Q1,01)
Id 7  PX SEND PARTITION (KEY) :TQ10000 (Q1,00)           검수내역: 파티션 키에 맞춰 재분배(생산자)
Id 9  TABLE ACCESS FULL 검수내역 (Q1,00)
Id 3  HASH JOIN (Q1,01) ← Id 4(운송기록)·Id 6 PX RECEIVE(검수내역)를 받아 조인
```

- 운송기록(Id 5)은 이미 운송장번호 해시 16 파티션으로 나뉘어 있으므로, 조인 서버 집합 **Q1,01**이 Id 4 `PX PARTITION HASH ALL`로 **각자 자기 파티션을 그대로** 읽습니다. 위에 `PX SEND`가 없다는 것이 곧 **재분배 없음**의 표식입니다.
- 검수내역(Id 9)은 파티셔닝돼 있지 않으므로 그대로는 운송기록의 파티션과 맞물릴 수 없습니다. 그래서 생산자 집합 **Q1,00**이 Id 7 `PX SEND PARTITION (KEY)`로 검수내역을 **운송기록의 파티션 경계에 맞춰** 재분배하고, Id 6 `PX RECEIVE`가 Q1,01에서 받습니다.

즉 **한쪽(운송기록)은 재분배 없이 파티션 로컬, 다른 쪽(검수내역)만 파티션 키로 재분배**하는 이 방식이 **부분(partial) 파티션 와이즈 조인**입니다. 양쪽을 다 재분배하는 hash-hash와 달리 큰 테이블(운송기록 1억 9천만)을 네트워크로 흘리지 않아, 재분배량이 검수내역 한쪽으로 국한됩니다.

```text
② partial PWJ : 운송기록 = SEND 없음(PARTITION HASH ALL), 검수내역 = SEND PARTITION(KEY)  → Id 4·Id 7과 일치   ✔
① full PWJ    : 양쪽 다 SEND 없음(둘 다 같은 키로 파티셔닝)                                → 검수내역에 Id 7 SEND 있음
③ hash-hash   : 양쪽 다 SEND HASH                                                        → 운송기록엔 SEND 자체가 없음
④ 역할 뒤바꿈  : 검수내역=로컬, 운송기록=SEND PARTITION(KEY)                              → Id 4·Id 7과 반대(값 스왑)
```

`PX SEND`가 검수내역 쪽(Id 7)에만 있고 운송기록 쪽엔 없다는 사실이 full PWJ와 hash-hash를 함께 배제합니다. 그리고 재분배되는 쪽은 **파티셔닝 안 된 검수내역**이므로 ④처럼 역할을 뒤바꾼 진술도 틀립니다. 따라서 ②가 옳습니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ✗ | 검수내역은 파티셔닝돼 있지 않다고 발문이 못박았으므로 대응 파티션 쌍 자체가 없습니다. full 파티션 와이즈면 양쪽 조인 입력에 `PX SEND`가 없어야 하는데 Id 7에 `PX SEND PARTITION (KEY)`가 걸려 있고, Id 7은 QC로 넘기는 통로도 아닙니다 — QC 전송은 P->S인 Id 2 `PX SEND QC (RANDOM)`입니다 |
| ② | **○** | 운송기록은 Id 4 `PX PARTITION HASH ALL`로 재분배 없이 파티션 로컬 읽기, 검수내역만 Id 7 `PX SEND PARTITION (KEY)`로 운송기록 파티션에 맞춰 재분배 — 부분 파티션 와이즈 조인과 일치합니다 |
| ③ | ✗ | 두 테이블 큐가 있다는 것은 사실이나 :TQ10001은 조인 결과를 QC로 보내는 Id 2용이지 분배용이 아닙니다. hash-hash면 Id 5·Id 9 위에 각각 `PX SEND HASH`가 있어야 하는데 운송기록 쪽엔 `PX SEND`가 아예 없고(Id 4는 PCWC 파티션 스캔), 검수내역 쪽도 `SEND HASH`가 아니라 `SEND PARTITION (KEY)`입니다 |
| ④ | ✗ | 재분배되는 쪽과 로컬로 읽는 쪽을 뒤바꿨습니다. Id 7 `PX SEND PARTITION (KEY)`가 걸린 것은 Id 8 `PX BLOCK ITERATOR`로 읽히는 검수내역이고, Id 4 `PX PARTITION HASH ALL`로 파티션 로컬 읽기를 하는 쪽이 운송기록입니다. 파티셔닝 안 된 검수내역을 로컬 기준으로 삼을 수도 없습니다 |

---

## ✅ 이 문제의 핵심

1. **부분(partial) 파티션 와이즈 조인은 한쪽만 재분배**합니다. 이미 조인 키로 파티셔닝된 운송기록은 재분배 없이 파티션 로컬로 읽고, 안 나뉜 검수내역만 그 경계에 맞춰 재분배합니다.
2. **재분배 여부는 `PX SEND` 유무로 판별**합니다. 운송기록 위엔 SEND가 없고(Id 4 PX PARTITION HASH ALL), 검수내역 위엔 Id 7 `PX SEND PARTITION (KEY)`가 있습니다.
3. **`SEND PARTITION (KEY)`는 상대 테이블의 파티션 경계에 맞추는 재분배**입니다. 조인 키 해시로 새 버킷을 만드는 hash-hash의 `SEND HASH`와 다릅니다.
4. **어느 쪽이 재분배되는지가 판별의 핵심**입니다. 재분배되는 쪽은 파티셔닝 안 된 검수내역이며, 이를 운송기록과 뒤바꾸면 틀린 진술이 됩니다.

📌 한 줄 정리: 운송기록은 Id 4 `PX PARTITION HASH ALL`로 재분배 없이 파티션 로컬로 읽고 검수내역만 Id 7 `PX SEND PARTITION (KEY)`로 운송기록 파티션에 맞춰 재분배하므로, 큰 테이블을 흘리지 않는 부분 파티션 와이즈 조인입니다.
