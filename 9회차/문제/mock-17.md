<!--meta
번호: 17
대상장: 6
대상절: 6.5
절제목: 대용량 배치 프로그램 튜닝
문제유형: 직접지목형
보조자료: 실행계획
DBMS: 오라클
정답: 1
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

재난지원금 지급 정산 야간 배치가 `지급신청`(약 3억 2천만 건)과 `지원유형`(약 700건)을 **지원유형코드로 조인**해 지원유형별 지급총액을 집계한다. `지급신청`은 지원유형 기준 파티션이 아니며, `지원유형`은 소형 코드성 테이블이다. 아래 병렬 실행계획에서 두 테이블이 병렬 서버(Slave) 사이에 어떤 분배 방식으로 조인되는지 직접 지목한 설명으로 가장 적절한 것은?

#### [아 래]

```text
| Id  | Operation                     | Name       | Pstart| Pstop | TQ    |IN-OUT|
|-----|-------------------------------|------------|-------|-------|-------|------|
|   0 | SELECT STATEMENT              |            |       |       |       |      |
|   1 |  PX COORDINATOR               |            |       |       |       |      |
|   2 |   PX SEND QC (RANDOM)         | :TQ10001   |       |       | Q1,01 | P->S |
|   3 |    HASH GROUP BY              |            |       |       | Q1,01 | PCWP |
|*  4 |     HASH JOIN                 |            |       |       | Q1,01 | PCWP |
|   5 |      PX RECEIVE               |            |       |       | Q1,01 | PCWP |
|   6 |       PX SEND BROADCAST       | :TQ10000   |       |       | Q1,00 | P->P |
|   7 |        PX BLOCK ITERATOR      |            |       |       | Q1,00 | PCWC |
|   8 |         TABLE ACCESS FULL     | 지원유형   |       |       | Q1,00 | PCWP |
|   9 |      PX BLOCK ITERATOR        |            |       |       | Q1,01 | PCWC |
|  10 |       TABLE ACCESS FULL       | 지급신청   |       |       | Q1,01 | PCWP |
```

### 선택지

① 소형 지원유형(Id 8)을 `PX SEND BROADCAST`(Id 6)로 모든 병렬 서버에 복제하고, 대형 지급신청(Id 10)은 재분배 없이 각 서버가 `PX BLOCK ITERATOR`(Id 9)로 자기 블록 범위만 읽어 조인하는 broadcast 분배다. 대형을 재분배하는 대신 700건짜리 소형을 복제하는 편이 싸기 때문이다.

② 조인 키 지원유형코드의 해시로 지급신청과 지원유형을 **양쪽 모두 재분배(hash-hash)** 한 뒤 각 서버가 자기 버킷 범위의 행만 Id 4 `HASH JOIN`에서 맞대며, 그 재분배가 Id 6의 `:TQ10000`과 Id 9에서 각각 일어나 두 갈래 테이블 큐로 나뉘고 Id 5 `PX RECEIVE`가 양쪽 결과를 함께 받는다.

③ 두 테이블이 지원유형코드로 동일하게 파티셔닝돼 있어 재분배 없이 대응 파티션 집합만 로컬로 조인하는 (full) 파티션 와이즈 조인이며, Id 8·Id 10이 같은 PX PARTITION 아래에서 읽힌다. Pstart·Pstop이 비어 있는 것도 각 서버가 파티션 쌍을 통째로 맡았다는 표시다.

④ 대형 지급신청만 Id 9 `PX BLOCK ITERATOR`로 각 서버가 파티션 단위로 읽고, 소형 지원유형을 지급신청의 파티션 경계에 맞춰 Id 6에서 `PX SEND PARTITION (KEY)`로 재분배하는 부분(partial) 파티션 와이즈 조인이다. Id 5 `PX RECEIVE`도 자기 파티션 몫만 받으므로 700건이 전 서버에 복제되지는 않는다.

---

### 정답 — ①

### 왜 ①인가

분배 방식은 **어느 입력이 `PX SEND`를 거치고 그 SEND의 종류가 무엇인지**로 읽습니다.

```text
Id 6  PX SEND BROADCAST :TQ10000 (Q1,00 → 모든 서버)   소형 지원유형을 전 서버에 복제
Id 7   PX BLOCK ITERATOR (Q1,00)                        지원유형 블록 스캔
Id 8    TABLE ACCESS FULL 지원유형 (약 700건)            복제 대상 — 작다
Id 9  PX BLOCK ITERATOR (Q1,01)                          지급신청을 각 서버가 자기 블록만
Id 10  TABLE ACCESS FULL 지급신청 (약 3.2억 건)          재분배 SEND 없음
```

- 플랜에서 조인 입력 중 `PX SEND`를 거치는 쪽은 **지원유형(Id 8) 하나뿐**이고, 그 SEND는 `PX SEND BROADCAST`(Id 6)입니다. 즉 소형 지원유형을 모든 병렬 서버에 **복제**합니다.
- 대형 지급신청(Id 10)은 위에 아무 SEND가 없고 `PX BLOCK ITERATOR`(Id 9)로 각 서버가 자기 블록 범위만 읽습니다. **재분배되지 않습니다.**
- 이 조합이 broadcast 분배입니다. 3억 건이 넘는 지급신청을 해시로 재분배하면 그 큰 집합 전체가 서버 사이를 오가야 하지만, 700건짜리 지원유형을 복제하면 트래픽이 미미합니다. 그래서 **대형×소형** 조인에서 옵티마이저가 소형 broadcast를 고른 것입니다.

```text
① broadcast    : 소형 쪽에 PX SEND BROADCAST(Id 6), 대형은 SEND 없음   → Id 6·9·10과 일치   ✔
② hash-hash    : 양쪽 위에 각각 PX SEND HASH                            → 대형 지급신청엔 SEND 없음
③ full PWJ     : 두 입력이 같은 PX PARTITION 아래, SEND 없음            → 소형에 BROADCAST SEND 있음
④ partial PWJ  : 소형에 PX SEND PARTITION (KEY)                         → SEND 종류가 BROADCAST
```

유일한 조인 입력 SEND가 `PX SEND BROADCAST` 하나라는 사실이 hash-hash·full PWJ·partial PWJ를 한꺼번에 배제합니다. 따라서 ①이 옳습니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | **○** | 조인 입력 중 SEND를 거치는 쪽은 소형 지원유형(Id 8)뿐이고 그 SEND가 `PX SEND BROADCAST`(Id 6), 대형 지급신청(Id 10)은 SEND 없이 `PX BLOCK ITERATOR`로 로컬 스캔 — 대형×소형에서 소형을 복제하는 broadcast 분배입니다 |
| ② | ✗ | hash-hash면 두 입력 위에 각각 `PX SEND HASH`가 있어야 하는데, 대형 지급신청(Id 10) 위엔 SEND가 없이 Id 9 `PX BLOCK ITERATOR`뿐이고 소형 쪽 Id 6은 SEND HASH가 아니라 SEND BROADCAST입니다. 조인 입력 테이블 큐도 `:TQ10000` 하나뿐이라 '두 갈래'가 성립하지 않는, 분배 방식을 broadcast에서 hash-hash로 뒤바꾼 진술입니다 |
| ③ | ✗ | full 파티션 와이즈면 두 입력이 같은 `PX PARTITION` 아래에서 SEND 없이 읽혀야 하는데, 지원유형은 `PX SEND BROADCAST`(Id 6)로 복제되고 있고 지급신청은 지원유형 기준 파티션도 아닙니다. Pstart·Pstop이 빈 것은 파티션 액세스가 없다는 뜻이지 파티션 쌍을 맡았다는 표시가 아니므로, broadcast를 PWJ로 뒤바꾼 값스왑입니다 |
| ④ | ✗ | partial 파티션 와이즈면 재분배되는 소형 쪽에 `PX SEND PARTITION (KEY)`가 있어야 하는데, Id 6의 SEND는 `BROADCAST`이고 Id 5 `PX RECEIVE`는 700건 전량을 받습니다. Id 9 `PX BLOCK ITERATOR`도 파티션 단위가 아니라 블록 범위 단위 분할이라, SEND 종류를 BROADCAST에서 PARTITION (KEY)로 뒤바꾼 진술입니다 |

---

## ✅ 이 문제의 핵심

1. **분배 방식은 조인 입력의 `PX SEND` 종류로 판별**합니다. 여기서 조인 입력 SEND는 `PX SEND BROADCAST`(Id 6) 하나뿐입니다.
2. **broadcast는 대형×소형에서 소형을 전 서버에 복제**하는 방식입니다. 700건짜리 지원유형을 복제하고, 3.2억 건 지급신청은 재분배 없이 각 서버가 블록 단위로 읽습니다.
3. **대형 지급신청 위에 SEND가 없다는 것이 핵심 단서**입니다. Id 9 `PX BLOCK ITERATOR`로 로컬 스캔만 하므로 큰 집합이 서버 사이를 오가지 않습니다.
4. **hash-hash·full PWJ·partial PWJ는 각각 `PX SEND HASH`·같은 PX PARTITION 아래·`PX SEND PARTITION (KEY)`가 있어야** 성립합니다. 이 플랜의 SEND는 BROADCAST뿐이라 셋 다 배제됩니다 — 분배 방식을 뒤바꾼 값스왑 오답입니다.

📌 한 줄 정리: 조인 입력 중 소형 지원유형(Id 8)만 `PX SEND BROADCAST`(Id 6)로 전 서버에 복제되고 대형 지급신청(Id 10)은 SEND 없이 `PX BLOCK ITERATOR`로 로컬 스캔하므로, 대형을 재분배하는 대신 소형을 복제한 broadcast 분배다.
