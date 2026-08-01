<!--meta
번호: 17
대상장: 6
대상절: 6.5
절제목: 대용량 배치 프로그램 튜닝
문제유형: 직접지목형
보조자료: 실행계획
DBMS: 오라클
정답: 3
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

처방전 테이블(약 2억 2천만 건)과 조제내역 테이블(약 8,900만 건)을 처방ID로 병렬 해시 조인하는 야간 정산 배치 SQL의 실행계획이다. 두 테이블은 파티셔닝돼 있지 않고, 어느 쪽도 조인 키로 미리 나뉘어 있지 않다. 이 병렬 실행계획은 두 테이블을 병렬 서버(Slave) 사이에 **어떻게 분배**하고 있는가? 가장 정확히 설명한 것은?

#### [아 래]

```text
| Id  | Operation                  | Name       | Pstart| Pstop | TQ    |IN-OUT|
|-----|----------------------------|------------|-------|-------|-------|------|
|   0 | SELECT STATEMENT           |            |       |       |       |      |
|   1 |  PX COORDINATOR            |            |       |       |       |      |
|   2 |   PX SEND QC (RANDOM)      | :TQ10002   |       |       | Q1,02 | P->S |
|*  3 |    HASH JOIN               |            |       |       | Q1,02 | PCWP |
|   4 |     PX RECEIVE             |            |       |       | Q1,02 | PCWP |
|   5 |      PX SEND HASH          | :TQ10000   |       |       | Q1,00 | P->P |
|   6 |       PX BLOCK ITERATOR    |            |       |       | Q1,00 | PCWC |
|   7 |        TABLE ACCESS FULL   | 처방전      |       |       | Q1,00 | PCWP |
|   8 |     PX RECEIVE             |            |       |       | Q1,02 | PCWP |
|   9 |      PX SEND HASH          | :TQ10001   |       |       | Q1,01 | P->P |
|  10 |       PX BLOCK ITERATOR    |            |       |       | Q1,01 | PCWC |
|  11 |        TABLE ACCESS FULL   | 조제내역    |       |       | Q1,01 | PCWP |
```

### 선택지

① 처방전 2억 2천만 건과 조제내역 8,900만 건이 처방ID로 동일하게 파티셔닝돼 있어, Id 6·Id 10의 `PX BLOCK ITERATOR`가 각 서버에 대응 파티션 쌍을 하나씩 맡기고 Id 3 `HASH JOIN`이 서버 간 전송 없이 각자 로컬에서 끝내는 파티션 와이즈(partition-wise) 조인이다.

② 작은 쪽인 조제내역 8,900만 건을 Id 9에서 병렬 서버 전체에 복제(broadcast)해 Q1,02의 각 서버가 사본을 갖게 하고, 큰 쪽인 처방전은 Id 6 `PX BLOCK ITERATOR`로 자기 조각만 스캔해 재분배 없이 Id 3 `HASH JOIN`에서 맞물리는 broadcast-none 분배다.

③ 처방전과 조제내역을 **양쪽 다 조인 키(처방ID) 해시로 재분배**한다(hash-hash). 두 테이블 모두 대형이라 소형을 전체 복제하는 broadcast는 각 서버에 큰 테이블을 통째로 반복 복제해 비용이 과다하므로, 각 입력을 PX SEND HASH로 한 번씩만 재분배해 같은 해시 버킷끼리 조인한다.

④ 큰 쪽인 처방전을 Id 5 `PX SEND HASH :TQ10000`으로 처방ID 해시 재분배하고, 작은 쪽인 조제내역은 Id 9에서 병렬 서버 전체에 복제(broadcast)해 Id 8 `PX RECEIVE`가 사본을 받는 hash-broadcast 분배다. TQ가 :TQ10000과 :TQ10001로 갈린 것이 두 입력의 분배 방식이 서로 다르다는 표시다.

---

### 정답 — ③

### 왜 ③인가

분배 방식은 **조인(Id 3)의 두 입력이 각각 어떤 PX SEND를 거치는지**로 읽습니다.

```text
Id 5  PX SEND HASH  :TQ10000  (Q1,00)   처방전 쪽 생산자 → 조인 키 해시로 재분배
Id 7  TABLE ACCESS FULL 처방전 (Q1,00)
Id 9  PX SEND HASH  :TQ10001  (Q1,01)   조제내역 쪽 생산자 → 조인 키 해시로 재분배
Id 11 TABLE ACCESS FULL 조제내역 (Q1,01)
Id 3  HASH JOIN (Q1,02) ← Id 4·Id 8 PX RECEIVE로 양쪽을 받아 조인
```

- 처방전(Id 7)은 Id 5 `PX SEND HASH`로, 조제내역(Id 11)은 Id 9 `PX SEND HASH`로 **양쪽 모두** 조인 키(처방ID) 해시에 따라 재분배됩니다.
- 재분배된 두 스트림을 조인 소비자 집합(**Q1,02**)의 Id 4·Id 8 `PX RECEIVE`가 받아 Id 3 `HASH JOIN`에서 **같은 해시 버킷 범위의 양쪽 행만** 맞물려 조인합니다.

양쪽에 `PX SEND HASH`가 있는 이 방식이 **hash-hash 분배**입니다. 여기서 broadcast를 쓰지 않은 이유가 발문의 핵심입니다. broadcast는 한쪽 테이블을 **모든 병렬 서버에 통째로 복제**하는 방식이라, 소형이 아주 작을 때만 이득입니다. 그런데 이 조인은 작은 쪽(조제내역)도 8,900만 건으로 대형이라, 이를 서버 수만큼 복제하면 복제량이 폭증합니다. 그래서 각 입력을 **한 번씩만** 해시 재분배하는 hash-hash가 선택됩니다.

```text
③ hash-hash      : 처방전 = SEND HASH,  조제내역 = SEND HASH   → Id 5·Id 9와 일치        ✔
② broadcast-none : 소형 = SEND BROADCAST, 대형 = 로컬 스캔      → BROADCAST 노드 없음
① partition-wise : 조인 입력에 PX SEND 없음                     → Id 5·Id 9에 SEND HASH 있음
④ hash-broadcast : 한쪽 SEND HASH + 다른 쪽 SEND BROADCAST      → 양쪽 다 SEND HASH라 불일치
```

조인 입력 양쪽에 `PX SEND HASH`가 나란히 있다는 사실이 broadcast·partition-wise 계열을 모두 배제합니다. 따라서 ③이 옳습니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ✗ | 파티션 와이즈면 조인 입력에 PX SEND가 없어야 하는데 Id 5·Id 9에 `PX SEND HASH`가 있고, TQ도 Q1,00·Q1,01에서 Q1,02로 갈아탑니다. 발문상 두 테이블은 파티셔닝돼 있지도 않으므로 파티션 쌍 로컬 조인이 아닙니다 |
| ② | ✗ | broadcast-none이면 소형 쪽에 `PX SEND BROADCAST`가 있고 대형 쪽에는 SEND가 없어야 하는데, 플랜에 BROADCAST 노드가 없고 처방전도 Id 5 `PX SEND HASH`로 재분배됩니다. 조제내역 역시 Id 9 `PX SEND HASH`입니다 |
| ③ | **○** | Id 5·Id 9가 모두 `PX SEND HASH`로, 처방전·조제내역을 양쪽 다 처방ID 해시로 재분배합니다. 둘 다 대형이라 broadcast 대신 hash-hash를 쓴 상황과 일치합니다 |
| ④ | ✗ | hash-broadcast면 한쪽만 `PX SEND HASH`, 다른 쪽은 `PX SEND BROADCAST`여야 합니다. Id 5·Id 9 둘 다 `PX SEND HASH`이고, TQ가 :TQ10000·:TQ10001로 갈린 것은 생산자 집합이 둘이라는 뜻일 뿐이라 분배 조합을 뒤바꾼 진술입니다 |

---

## ✅ 이 문제의 핵심

1. **조인 입력 양쪽에 `PX SEND HASH`가 있으면 hash-hash**입니다. 두 테이블을 각각 조인 키 해시로 한 번씩 재분배해 같은 버킷끼리 조인합니다.
2. **broadcast는 소형 한쪽만 전체 복제**합니다. 작은 쪽도 대형이면(8,900만 건) 서버 수만큼 복제 비용이 커져 broadcast가 불리하고, hash-hash가 유리합니다.
3. **분배 방식은 PX SEND 종류로 판별**합니다 — `SEND HASH`면 해시 재분배, `SEND BROADCAST`면 복제, 조인 입력에 SEND가 없으면 파티션 와이즈입니다.
4. **hash-hash·broadcast-none·hash-broadcast는 SEND 노드 구성이 서로 다릅니다.** 이 플랜은 양쪽 다 `SEND HASH`라 나머지 조합이 모두 배제됩니다.

📌 한 줄 정리: 조인 입력 처방전·조제내역이 Id 5·Id 9의 `PX SEND HASH`로 양쪽 다 처방ID 해시 재분배되어 Q1,02에서 같은 버킷끼리 조인하므로, 둘 다 대형이라 broadcast 대신 hash-hash를 택한 분배입니다.
