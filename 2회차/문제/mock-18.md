<!--meta
번호: 18
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

## 문제 18

### 문제

광고 노출이력 테이블(약 3억 건, 8개 파티션)과 캠페인 테이블(약 5천 건)을 병렬로 해시 조인하는 야간 정산 배치 SQL의 실행계획이다. 이 병렬 실행계획은 두 테이블을 병렬 서버(Slave) 사이에 **어떻게 분배**하고 있는가? 가장 정확히 설명한 것은?

#### [아 래]

```text
| Id  | Operation                  | Name       | Pstart| Pstop | TQ    |IN-OUT|
|-----|----------------------------|------------|-------|-------|-------|------|
|   0 | SELECT STATEMENT           |            |       |       |       |      |
|   1 |  PX COORDINATOR            |            |       |       |       |      |
|   2 |   PX SEND QC (RANDOM)      | :TQ10001   |       |       | Q1,01 | P->S |
|*  3 |    HASH JOIN               |            |       |       | Q1,01 | PCWP |
|   4 |     PX RECEIVE             |            |       |       | Q1,01 | PCWP |
|   5 |      PX SEND BROADCAST     | :TQ10000   |       |       | Q1,00 | P->P |
|   6 |       PX BLOCK ITERATOR    |            |       |       | Q1,00 | PCWC |
|   7 |        TABLE ACCESS FULL   | 캠페인      |       |       | Q1,00 | PCWP |
|   8 |     PX BLOCK ITERATOR      |            |     1 |     8 | Q1,01 | PCWC |
|*  9 |      TABLE ACCESS FULL     | 노출이력    |     1 |     8 | Q1,01 | PCWP |
```

### 선택지

① 노출이력과 캠페인을 양쪽 다 조인 키 해시로 재분배(hash-hash)하여, 각 서버가 자기 해시 버킷 범위의 양쪽 행만 조인한다.

② 캠페인(소형)을 병렬 서버 전체에 복제(broadcast)하고, 노출이력(대형)은 재분배 없이 각 서버가 PX BLOCK ITERATOR로 자기 파티션 조각만 스캔한다(broadcast-none).

③ 노출이력을 조인 키 해시로 재분배하고, 캠페인을 병렬 서버 전체에 복제한다(hash-broadcast).

④ 노출이력(대형)을 병렬 서버 전체에 복제(broadcast)하고, 캠페인(소형)은 각 서버가 자기 조각만 스캔한다.

---

### 정답 — ②

### 왜 ②인가

분배 방식은 각 생산자 TQ의 **PX SEND 종류**와, 조인 자식이 **PX SEND를 거치는지**로 읽습니다.

```text
Id 5  PX SEND BROADCAST  :TQ10000   캠페인 쪽 생산자 → 전체 복제
Id 7  TABLE ACCESS FULL  캠페인 (Q1,00)             → 소형 빌드 입력
Id 8  PX BLOCK ITERATOR  (Q1,01)    노출이력을 조인 슬레이브가 직접 스캔
Id 9  TABLE ACCESS FULL  노출이력 (Q1,01, Pstart 1~8) → PX SEND 없음
```

- Id 5는 캠페인(Id 7)을 읽어 **PX SEND BROADCAST**로 내보냅니다 → 소형 테이블을 병렬 서버 전체에 복제. Id 4 PX RECEIVE가 이를 받아 HASH JOIN의 빌드 입력이 됩니다.
- 노출이력(Id 9)은 **HASH JOIN과 같은 TQ(Q1,01)** 아래에서 Id 8 PX BLOCK ITERATOR로 직접 읽힙니다. 그 위에 **PX SEND/RECEIVE가 없습니다.** 즉 대형 테이블은 재분배되지 않고, 각 병렬 서버가 자기 파티션 조각(Pstart 1~8)만 스캔해 곧바로 조인의 탐침(probe) 입력으로 씁니다.

소형만 복제하고 대형은 재분배하지 않는 이 방식이 **broadcast-none 분배**이며 ②의 서술 그대로입니다. 대형을 옮기지 않으므로 3억 건 재분배 비용이 사라지는 것이 이 방식의 이점입니다.

나머지 셋은 실제 노드와 값을 바꿔치기한 것입니다.

```text
실제:  캠페인 = BROADCAST,  노출이력 = 재분배없음(로컬 스캔)   (② broadcast-none)   ✔
① hash-hash     : 캠페인 = HASH,      노출이력 = HASH       → SEND BROADCAST·SEND 부재와 불일치
③ hash-broadcast: 노출이력 = HASH,    캠페인 = BROADCAST     → 노출이력에 SEND HASH 없음
④ none-broadcast: 노출이력 = BROADCAST, 캠페인 = 로컬 스캔    → BROADCAST가 캠페인 쪽(Id 5)이라 대소를 뒤바꿈
```

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ✗ | `PX SEND HASH`가 어디에도 없습니다. 캠페인 쪽은 SEND BROADCAST(Id 5)이고 노출이력 쪽은 PX SEND 자체가 없어 hash-hash가 아닙니다 |
| ② | **○** | Id 5가 `PX SEND BROADCAST`(캠페인)이고, 노출이력은 조인과 같은 Q1,01 아래 Id 8 PX BLOCK ITERATOR로 SEND 없이 로컬 스캔됩니다. 소형만 복제하는 broadcast-none 분배입니다 |
| ③ | ✗ | 노출이력 쪽에 `PX SEND HASH`가 없고 재분배 노드도 없습니다. 노출이력은 Q1,01에서 로컬 스캔되므로 해시 재분배가 아닙니다 |
| ④ | ✗ | BROADCAST 노드는 캠페인 쪽 Id 5입니다. 노출이력은 복제되지 않고 로컬 스캔되므로, 대형·소형의 역할을 뒤바꾼 진술입니다 |

---

## ✅ 이 문제의 핵심

1. **분배 방식은 PX SEND의 종류로 판별**합니다 — `PX SEND BROADCAST`면 복제, `PX SEND HASH`면 해시 재분배입니다.
2. **한쪽에만 BROADCAST가 있고 다른 쪽은 PX SEND 없이 조인과 같은 TQ에서 스캔되면 broadcast-none**입니다. 대형은 재분배되지 않습니다.
3. **broadcast-none의 이점은 대형 테이블 재분배 제거**입니다. 소형 5천 건만 복제하고 3억 건은 각 서버가 자기 조각만 읽습니다.
4. **hash-hash·hash-broadcast는 `PX SEND HASH` 노드가 있어야** 성립합니다. 이 플랜엔 SEND HASH가 없습니다.

📌 한 줄 정리: 캠페인 쪽만 `PX SEND BROADCAST`로 복제되고 노출이력은 조인과 같은 Q1,01에서 PX SEND 없이 자기 파티션만 로컬 스캔하므로, 소형만 복제하는 broadcast-none 분배입니다.
