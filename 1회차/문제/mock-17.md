<!--meta
번호: 17
대상장: 6
대상절: 6.5
절제목: 대용량 배치
문제유형: 직접지목형
보조자료: 실행계획
DBMS: 오라클
정답: 1
선택지유형: 서술형
함정유형: [값스왑]
대상개념: [PQ_DISTRIBUTE, 병렬_조인]
자극물밀도: 실행계획_병렬_10행+
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 17

### 문제

거래이력 테이블(약 4억 건, 8개 파티션)과 계좌 테이블(약 2,400만 건, 4개 파티션)을 병렬로 해시 조인하는 야간 배치 SQL의 실행계획이다. 이 병렬 실행계획은 두 테이블을 병렬 서버(Slave) 사이에 **어떻게 분배**하고 있는가? 가장 정확히 설명한 것은?

#### [아 래]

```text
| Id  | Operation                  | Name       | Pstart| Pstop | TQ    |IN-OUT|
|-----|----------------------------|------------|-------|-------|-------|------|
|   0 | SELECT STATEMENT           |            |       |       |       |      |
|   1 |  PX COORDINATOR            |            |       |       |       |      |
|   2 |   PX SEND QC (RANDOM)      | :TQ10002   |       |       | Q1,02 | P->S |
|*  3 |    HASH JOIN BUFFERED      |            |       |       | Q1,02 | PCWP |
|   4 |     PX RECEIVE             |            |       |       | Q1,02 | PCWP |
|   5 |      PX SEND HASH          | :TQ10000   |       |       | Q1,00 | P->P |
|   6 |       PX BLOCK ITERATOR    |            |     1 |     8 | Q1,00 | PCWC |
|   7 |        TABLE ACCESS FULL   | 거래이력    |     1 |     8 | Q1,00 | PCWP |
|   8 |     PX RECEIVE             |            |       |       | Q1,02 | PCWP |
|   9 |      PX SEND HASH          | :TQ10001   |       |       | Q1,01 | P->P |
|  10 |       PX BLOCK ITERATOR    |            |     1 |     4 | Q1,01 | PCWC |
|  11 |        TABLE ACCESS FULL   | 계좌        |     1 |     4 | Q1,01 | PCWP |
```

### 선택지

① 거래이력과 계좌를 **모두 조인 키의 해시 값으로 재분배(hash-hash)** 하여, 각 병렬 서버가 자신에게 배정된 해시 버킷 범위의 양쪽 행만 조인한다.

② Id 5 `:TQ10000`이 거래이력 8개 파티션을 모든 서버에 복제(broadcast)하고, 계좌는 Id 10 `PX BLOCK ITERATOR`(1~4)로 각 서버가 자기 파티션만 스캔한다(broadcast-none).

③ Id 1 `PX COORDINATOR`가 `:TQ10000`과 `:TQ10001`을 먼저 받아 취합한 뒤, Id 3 `HASH JOIN BUFFERED`의 BUFFERED 표시대로 단일 서버가 순차 조인하므로 재분배가 없다.

④ 거래이력은 Id 5 `:TQ10000`에서 조인 키 해시로 재분배하지만, 계좌는 2,400만 건으로 작아 Id 9 `:TQ10001`이 4개 파티션 전체를 각 병렬 서버로 복제한다(hash-broadcast).

---

### 정답 — ①

### 왜 ①인가

분배 방식은 각 생산자 TQ의 **PX SEND 종류**로 읽습니다.

```text
Id 5  PX SEND HASH   :TQ10000  거래이력 쪽 생산자 → HASH 재분배
Id 9  PX SEND HASH   :TQ10001  계좌 쪽 생산자     → HASH 재분배
Id 3  HASH JOIN BUFFERED (:TQ10002)  두 스트림을 받아 조인
```

- Id 5는 거래이력(Id 7)을 읽어 **PX SEND HASH**로 내보냅니다 → 거래이력을 조인 키 해시로 재분배.
- Id 9는 계좌(Id 11)를 읽어 **PX SEND HASH**로 내보냅니다 → 계좌도 조인 키 해시로 재분배.
- 양쪽 모두 IN-OUT이 `P->P`(병렬→병렬)이고, `PX SEND BROADCAST`는 어디에도 없습니다.

두 입력이 **같은 해시 함수로 재분배**되므로, 같은 조인 키는 같은 병렬 서버로 모입니다. 각 서버는 자신이 맡은 해시 버킷 범위 안에서만 양쪽 행을 만나 조인합니다. 이것이 **hash-hash 분배**이고 ①의 서술 그대로입니다.

나머지 셋은 실제 노드와 값을 바꿔치기한 것입니다.

```text
실제:        거래이력 = HASH,      계좌 = HASH       (① hash-hash)   ✔
② broadcast-none : 거래이력 = BROADCAST, 계좌 = 재분배없음  → Id 5가 SEND HASH, 계좌도 Id 9로 재분배
④ hash-broadcast : 거래이력 = HASH,      계좌 = BROADCAST   → Id 9가 SEND HASH이므로 불일치
③ QC 단일서버    : 재분배 없음, 단일 서버 조인            → Id 3이 PCWP, P->S는 Id 2 하나뿐
```

②가 인용한 Pstart/Pstop `1~8`·`1~4`와 Id 10의 `PX BLOCK ITERATOR`는 실제 값이지만, 그것은 **각 테이블을 파티션 단위로 나눠 읽는 스캔 방식**일 뿐 분배 방식이 아닙니다. 읽은 행은 곧바로 Id 5·Id 9의 `PX SEND HASH`로 넘어가 재분배되므로 "계좌는 재분배 없음"이 성립하지 않고, 거래이력 쪽에도 BROADCAST 노드가 없습니다.

④가 말한 계좌 2,400만 건 역시 문제의 서술 그대로지만, 크기가 작다고 옵티마이저가 broadcast를 택했는지는 **Id 9의 노드 이름**으로 판정합니다. `:TQ10001`은 `PX SEND BROADCAST`가 아니라 `PX SEND HASH`이므로 hash-broadcast가 아닙니다.

③이 근거로 든 `HASH JOIN BUFFERED`의 BUFFERED는 소비자가 한쪽 스트림을 **버퍼에 담아 두는 것**을 뜻할 뿐 직렬화가 아닙니다. Id 3의 IN-OUT은 `PCWP`(병렬 서버가 직접 수행)이고 `P->S`는 QC로 결과를 올리는 Id 2 한 곳뿐이므로, 조인은 병렬 서버들이 나눠 수행합니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | **○** | Id 5·Id 9가 둘 다 `PX SEND HASH`(P->P)이고 BROADCAST가 없습니다. 양쪽을 조인 키 해시로 재분배하는 hash-hash 분배입니다 |
| ② | ✗ | Id 10의 `PX BLOCK ITERATOR`(1~4)는 스캔 방식일 뿐 분배가 아닙니다. 계좌도 Id 9 `PX SEND HASH`로 재분배되고, Id 5 역시 BROADCAST가 아닌 `PX SEND HASH`입니다 |
| ③ | ✗ | `HASH JOIN BUFFERED`의 BUFFERED는 스트림 버퍼링이지 직렬화가 아닙니다. Id 3은 `PCWP`로 병렬 수행되고 `P->S`는 QC로 올리는 Id 2뿐이며, 두 생산자 TQ는 `P->P`입니다 |
| ④ | ✗ | 계좌가 2,400만 건인 것은 맞지만 분배는 노드 이름으로 판정합니다. Id 9 `:TQ10001`은 `PX SEND BROADCAST`가 아니라 `PX SEND HASH`이므로 한쪽만 해시인 hash-broadcast가 아닙니다 |

---

## ✅ 이 문제의 핵심

1. **분배 방식은 PX SEND의 종류로 판별**합니다 — `PX SEND HASH`면 해시 재분배, `PX SEND BROADCAST`면 복제입니다.
2. **양쪽 생산자 TQ가 모두 SEND HASH이고 P->P면 hash-hash 분배**입니다. 같은 키가 같은 서버로 모여 버킷 단위로 조인됩니다.
3. **broadcast-none·hash-broadcast는 한쪽에 BROADCAST 노드가 있어야** 성립합니다. 이 플랜엔 없습니다.
4. **`P->P`(병렬→병렬) IN-OUT은 재분배가 일어남**을 뜻합니다. QC로 모아 단일 서버에서 조인하는 구조가 아닙니다.

📌 한 줄 정리: 거래이력·계좌 양쪽 생산자 모두 `PX SEND HASH`(P->P)로 내보내고 BROADCAST 노드가 없으므로, 두 테이블을 조인 키 해시로 재분배하는 hash-hash 분배입니다.
