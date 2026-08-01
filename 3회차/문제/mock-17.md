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
대상개념: [PQ_DISTRIBUTE, 병렬_조인, Partition_Wise_Join]
자극물밀도: 실행계획_병렬_10행+
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 17

### 문제

펀드거래 테이블(약 4.8억 건)과 펀드잔고 테이블(약 6,400만 건)은 **모두 투자자ID로 32개 해시 파티션**으로 나뉘어 있다. 두 테이블을 투자자ID로 조인하고 펀드유형별로 집계하는 야간 정산 배치 SQL의 병렬 실행계획이다. 이 플랜에서 두 테이블은 병렬 서버(Slave) 사이에 **어떻게 분배되어 조인**되는가? 가장 정확히 설명한 것은?

#### [아 래]

```text
| Id  | Operation                    | Name       | Pstart| Pstop | TQ    |IN-OUT|
|-----|------------------------------|------------|-------|-------|-------|------|
|   0 | SELECT STATEMENT             |            |       |       |       |      |
|   1 |  PX COORDINATOR              |            |       |       |       |      |
|   2 |   PX SEND QC (RANDOM)        | :TQ10001   |       |       | Q1,01 | P->S |
|   3 |    HASH GROUP BY             |            |       |       | Q1,01 | PCWP |
|   4 |     PX RECEIVE               |            |       |       | Q1,01 | PCWP |
|   5 |      PX SEND HASH            | :TQ10000   |       |       | Q1,00 | P->P |
|   6 |       HASH GROUP BY          |            |       |       | Q1,00 | PCWP |
|   7 |        PX PARTITION HASH ALL |            |     1 |    32 | Q1,00 | PCWC |
|*  8 |         HASH JOIN            |            |       |       | Q1,00 | PCWP |
|   9 |          TABLE ACCESS FULL   | 펀드거래    |     1 |    32 | Q1,00 | PCWP |
|  10 |          TABLE ACCESS FULL   | 펀드잔고    |     1 |    32 | Q1,00 | PCWP |
```

### 선택지

① 소형 펀드잔고(약 6,400만 건)를 Id 5 PX SEND HASH 경로로 병렬 서버 전체에 복제(broadcast)하고, 대형 펀드거래(약 4.8억 건)는 Id 9에서 Pstart 1~Pstop 32 그대로 각 서버가 자기 조각만 스캔해 재분배하지 않는 broadcast-none 분배다. 복제본이 각 서버 HASH JOIN(Id 8)의 빌드 입력이 되고 조인 키 재분배는 없다.

② 두 테이블을 조인 키 투자자ID의 해시로 양쪽 재분배(hash-hash)한 뒤 각 병렬 서버가 자기 버킷 범위의 투자자ID 행만 짝지어 HASH JOIN(Id 8)한다. 그 재분배가 Id 5 PX SEND HASH이고 받는 쪽이 Id 4 PX RECEIVE이며, Id 7 PX PARTITION HASH ALL의 1~32는 서버가 맡은 버킷 범위 표시다.

③ 두 테이블이 투자자ID로 동일하게 32개 해시 파티셔닝돼 있어 PX PARTITION HASH ALL(Id 7) 아래에서 각 병렬 서버가 대응하는 파티션 쌍만 HASH JOIN(Id 8)한다. 조인 입력 펀드거래·펀드잔고(Id 9·10)가 같은 Q1,00에서 PX SEND 없이 읽히므로 조인을 위한 재분배가 없는 파티션 와이즈 조인이다.

④ 대형 펀드거래(약 4.8억 건)를 Id 5 PX SEND HASH로 투자자ID 해시 재분배하고, 소형 펀드잔고(약 6,400만 건)는 병렬 서버 전체에 복제(broadcast)해 각 서버가 전체 사본을 들고 HASH JOIN(Id 8)하는 hash-broadcast 분배다. Id 7의 Pstart 1~Pstop 32는 복제 대상 파티션 범위를 가리킨다.

---

### 정답 — ③

### 왜 ③인가

분배 방식은 **조인 노드(Id 8)의 두 입력이 PX SEND를 거치는지**, 그리고 조인을 감싸는 노드가 무엇인지로 읽습니다.

```text
Id 7  PX PARTITION HASH ALL (Pstart 1~Pstop 32)   조인을 파티션 단위로 감쌈
Id 8   HASH JOIN (Q1,00)                           파티션 쌍 내부에서 조인
Id 9    TABLE ACCESS FULL 펀드거래 (Q1,00, 1~32)   조인 입력 — PX SEND 없음
Id 10   TABLE ACCESS FULL 펀드잔고 (Q1,00, 1~32)   조인 입력 — PX SEND 없음
```

- 두 조인 입력(Id 9·10)은 **같은 TQ(Q1,00)** 아래에서, **같은 PX PARTITION HASH ALL(Id 7)** 안에서 읽힙니다. 그 사이 어디에도 `PX SEND`/`PX RECEIVE`가 없습니다. 두 테이블이 투자자ID로 동일하게 32개 해시 파티셔닝돼 있으므로, 각 병렬 서버가 **대응하는 파티션 쌍(펀드거래 p_k ↔ 펀드잔고 p_k)만** 맞들어 조인합니다. 이것이 재분배가 사라지는 **(full) 파티션 와이즈 조인**입니다.
- 플랜에 유일하게 있는 `PX SEND HASH`(Id 5)는 **조인 위쪽**입니다. 조인·부분집계(Id 6 HASH GROUP BY)를 마친 결과를 **펀드유형**으로 다시 해시 재분배해 최종 HASH GROUP BY(Id 3)로 넘기는, **집계용 재분배**입니다. 조인 키(투자자ID) 재분배가 아닙니다.

```text
조인 분배(Id 7~10) : 재분배 없음 — 동일 파티셔닝으로 파티션 쌍 로컬 조인   → 파티션 와이즈  ✔
Id 5 PX SEND HASH  : 펀드유형 집계용 재분배 (조인 아님)
Id 4 PX RECEIVE    : Id 5가 보낸 부분집계 결과를 받는 쪽 (조인 입력 아님)
Id 7 Pstart 1~32   : 조인 대상 파티션 번호 범위 (버킷 범위·복제 범위 아님)
```

조인 입력에 SEND가 없다는 사실이 hash-hash·broadcast 계열을 모두 배제합니다. 따라서 ③이 옳습니다.

나머지 셋은 노드와 분배 방식을 뒤바꾼 값스왑입니다.

```text
② hash-hash     : 조인 입력(Id 9·10)에 PX SEND HASH가 있어야 성립 → 없음
                  Id 5·4는 조인 위(Id 6 HASH GROUP BY 다음) 집계용 TQ
① broadcast-none: PX SEND BROADCAST 노드가 어디에도 없음
                  Id 5는 SEND HASH지 SEND BROADCAST가 아니므로 복제 경로가 될 수 없음
④ hash-broadcast: PX SEND HASH·PX SEND BROADCAST 둘 다 조인 입력에 없음
                  Id 7의 1~32는 PX PARTITION HASH ALL이 훑는 파티션 번호지 복제 범위가 아님
```

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ✗ | broadcast-none이면 소형 쪽에 `PX SEND BROADCAST`가 있어야 하는데 플랜에 BROADCAST 노드가 없습니다. Id 5는 SEND HASH라 복제 경로가 될 수 없고, 그마저 조인 위(Id 6 다음)에 있습니다. Id 9·10 모두 Pstart 1~Pstop 32의 파티션 단위 로컬 스캔입니다 |
| ② | ✗ | hash-hash면 조인 입력 양쪽에 `PX SEND HASH`가 있어야 합니다. Id 9·10엔 SEND가 없고, Id 5 SEND HASH와 Id 4 PX RECEIVE는 Id 6 HASH GROUP BY 위쪽 TQ라 집계용입니다. Id 7의 1~32도 버킷 범위가 아니라 훑는 파티션 번호입니다 |
| ③ | **○** | 조인 입력 Id 9·10이 같은 Q1,00·같은 PX PARTITION HASH ALL(Id 7) 아래에서 PX SEND 없이 읽혀 파티션 쌍만 조인합니다. 동일 파티셔닝이 재분배를 없앤 파티션 와이즈 조인이며, 유일한 SEND(Id 5)는 조인 위 펀드유형 HASH GROUP BY 재분배입니다 |
| ④ | ✗ | hash-broadcast면 한쪽 `PX SEND HASH`+다른 쪽 `PX SEND BROADCAST`가 조인 입력에 있어야 합니다. Id 9·10엔 어느 SEND도 없고 플랜에 BROADCAST 노드 자체가 없습니다. Id 7의 Pstart 1~Pstop 32는 복제 범위가 아니라 조인이 훑는 파티션 번호입니다 |

---

## ✅ 이 문제의 핵심

1. **조인 분배는 조인 입력이 PX SEND를 거치는지로 판별**합니다. 두 입력(Id 9·10)에 SEND가 없고 같은 PX PARTITION HASH ALL(Id 7) 아래 있으면 파티션 와이즈 조인입니다.
2. **파티션 와이즈 조인의 조건은 양쪽이 조인 키로 동일 파티셔닝**된 것입니다. 각 서버가 대응 파티션 쌍만 로컬 조인해 재분배가 사라집니다.
3. **플랜 속 PX SEND HASH가 곧 조인 재분배는 아닙니다.** Id 5의 SEND HASH는 조인 위 펀드유형별 HASH GROUP BY를 위한 집계용 재분배입니다 — 위치(조인 아래 vs 위)를 확인해야 합니다.
4. **hash-hash·broadcast-none·hash-broadcast는 조인 입력에 `PX SEND HASH`/`PX SEND BROADCAST`가 있어야** 성립합니다. 이 플랜의 조인 입력엔 어느 SEND도 없습니다.

📌 한 줄 정리: 조인 입력 펀드거래·펀드잔고가 같은 Q1,00·같은 PX PARTITION HASH ALL 아래에서 PX SEND 없이 대응 파티션 쌍만 조인하므로 파티션 와이즈 조인이며, Id 5 PX SEND HASH는 조인이 아니라 펀드유형 집계용 재분배입니다.
