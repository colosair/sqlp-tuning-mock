<!--meta
번호: 17
대상장: 6
대상절: 6.5
절제목: 대용량 배치 프로그램 튜닝
문제유형: 적절한_것
보조자료: 실행계획
DBMS: 오라클
정답: 2
선택지유형: 서술형
함정유형: [값스왑]
대상개념: [Partition_Wise_Join, PQ_DISTRIBUTE, 병렬_조인]
자극물밀도: 실행계획_병렬_10행+
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 17

### 문제

가스 사용량 정산 야간 배치가 `사용량집계`(약 3억 6천만 건), `공급계약`(약 4,300만 건), `단가적용`(약 4,300만 건) 세 테이블을 **계약번호로 조인**해 계약번호별 정산액을 집계한다. 세 테이블은 **모두 계약번호 기준 해시 64 파티션**으로 나뉘어 있다. 아래 병렬 실행계획에서 세 테이블이 병렬 서버(Slave) 사이에 어떻게 분배되어 조인되는지에 대한 설명으로 가장 적절한 것은?

#### [아 래]

```text
| Id  | Operation                    | Name       | Pstart| Pstop | TQ    |IN-OUT|
|-----|------------------------------|------------|-------|-------|-------|------|
|   0 | SELECT STATEMENT             |            |       |       |       |      |
|   1 |  PX COORDINATOR              |            |       |       |       |      |
|   2 |   PX SEND QC (RANDOM)        | :TQ10000   |       |       | Q1,00 | P->S |
|   3 |    HASH GROUP BY             |            |       |       | Q1,00 | PCWP |
|   4 |     PX PARTITION HASH ALL    |            |     1 |    64 | Q1,00 | PCWC |
|*  5 |      HASH JOIN               |            |       |       | Q1,00 | PCWP |
|*  6 |       HASH JOIN              |            |       |       | Q1,00 | PCWP |
|   7 |        TABLE ACCESS FULL     | 사용량집계    |     1 |    64 | Q1,00 | PCWP |
|   8 |        TABLE ACCESS FULL     | 공급계약  |     1 |    64 | Q1,00 | PCWP |
|   9 |       TABLE ACCESS FULL      | 단가적용  |     1 |    64 | Q1,00 | PCWP |
```

### 선택지

① 대형 사용량집계만 파티션 단위로 각 서버가 자기 조각을 읽고, 공급계약·단가적용은 사용량집계의 파티션 경계에 맞춰 `PX SEND PARTITION (KEY)`로 재분배하는 부분(partial) 파티션 와이즈 조인이다.

② 세 테이블이 계약번호로 동일하게 64개 해시 파티셔닝돼 있어, 각 병렬 서버가 대응하는 파티션 집합만 로컬로 조인한다. 조인 입력 사용량집계·공급계약·단가적용(Id 7·8·9)이 같은 Q1,00·같은 PX PARTITION HASH ALL(Id 4) 아래에서 `PX SEND`/`PX RECEIVE` 없이 읽혀 재분배가 일어나지 않는 (full) 파티션 와이즈 조인이며, Id 3 HASH GROUP BY도 파티션 키(계약번호) 기준이라 서버 로컬로 끝난다.

③ 세 입력을 조인 키 계약번호의 해시로 각각 재분배(hash-hash)한 뒤 각 서버가 자기 버킷 범위의 행만 조인하며, 그 재분배가 Id 3에서 일어난다.

④ 소형 공급계약·단가적용을 병렬 서버 전체에 복제(broadcast)하고 대형 사용량집계만 재분배 없이 파티션 단위로 읽는 broadcast 분배다.

---

### 정답 — ②

### 왜 ②인가

분배 방식은 **조인 입력이 `PX SEND`를 거치는지**, 그리고 조인을 감싸는 노드가 무엇인지로 읽습니다.

```text
Id 4  PX PARTITION HASH ALL (Pstart 1~Pstop 64)   조인 전체를 파티션 단위로 감쌈
Id 5   HASH JOIN (Q1,00)                            파티션 집합 내부에서 조인
Id 6    HASH JOIN (Q1,00)                           파티션 집합 내부에서 조인
Id 7     TABLE ACCESS FULL 사용량집계 (Q1,00, 1~64)   조인 입력 — PX SEND 없음
Id 8     TABLE ACCESS FULL 공급계약 (Q1,00, 1~64) 조인 입력 — PX SEND 없음
Id 9     TABLE ACCESS FULL 단가적용 (Q1,00, 1~64) 조인 입력 — PX SEND 없음
```

- 세 조인 입력(Id 7·8·9)은 **같은 TQ(Q1,00)** 아래에서, **같은 `PX PARTITION HASH ALL`(Id 4)** 안에서 읽힙니다. 그 사이 어디에도 `PX SEND`/`PX RECEIVE`가 없습니다. 세 테이블이 계약번호로 동일하게 64개 해시 파티셔닝돼 있으므로, 각 병렬 서버가 **대응하는 파티션 집합(사용량집계 p_k ↔ 공급계약 p_k ↔ 단가적용 p_k)만** 맞들어 조인합니다. 이것이 재분배가 사라지는 **(full) 파티션 와이즈 조인**입니다.
- 플랜에 유일하게 있는 `PX SEND`는 최상단 Id 2 `PX SEND QC (RANDOM)` — 결과를 QC로 넘기는 마지막 단계뿐입니다. **조인 입력 사이의 재분배 SEND는 하나도 없습니다.**
- Id 3 `HASH GROUP BY`도 **집계 키가 파티션 키(계약번호)와 같습니다.** 한 계약번호의 행은 한 파티션(=한 서버)에만 있으므로, 집계 역시 서버 로컬로 끝나 별도의 재분배 TQ가 필요 없습니다. 그래서 이 플랜엔 TQ가 Q1,00 하나뿐입니다.

```text
② full PWJ    : 세 입력 모두 SEND 없음(같은 Id 4 PX PARTITION HASH ALL 아래)   → Id 7·8·9와 일치   ✔
① partial PWJ : 한쪽은 로컬, 다른 쪽에 PX SEND PARTITION (KEY)                 → 어느 입력에도 SEND 없음
③ hash-hash   : 세 입력 위에 각각 PX SEND HASH                                 → 조인 입력에 SEND 없음
④ broadcast   : 소형 쪽에 PX SEND BROADCAST                                    → BROADCAST 노드 자체가 없음
```

조인 입력에 `PX SEND`가 전혀 없다는 사실이 partial PWJ·hash-hash·broadcast를 한꺼번에 배제합니다. 따라서 ②가 옳습니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ✗ | partial 파티션 와이즈면 재분배되는 쪽에 `PX SEND PARTITION (KEY)`가 있어야 하는데, 공급계약·단가적용(Id 8·9) 위에 SEND가 없습니다. 세 테이블이 이미 같은 키로 파티셔닝돼 있어 한쪽만 재분배할 이유도 없습니다 |
| ② | **○** | 조인 입력 Id 7·8·9가 같은 Q1,00·같은 PX PARTITION HASH ALL(Id 4) 아래에서 SEND 없이 읽혀 대응 파티션 집합만 조인하고, Id 3 HASH GROUP BY도 파티션 키(계약번호) 기준이라 로컬로 끝나는 full 파티션 와이즈 조인입니다 |
| ③ | ✗ | hash-hash면 조인 입력 세 곳 위에 각각 `PX SEND HASH`가 있어야 합니다. Id 7·8·9엔 SEND가 없고, Id 3은 SEND HASH가 아니라 파티션 로컬 HASH GROUP BY입니다 |
| ④ | ✗ | broadcast면 소형 쪽에 `PX SEND BROADCAST`가 있어야 하는데 플랜에 BROADCAST 노드가 없습니다. 세 입력 모두 파티션 단위 로컬 스캔이라 복제 자체가 일어나지 않습니다 |

---

## ✅ 이 문제의 핵심

1. **full 파티션 와이즈 조인은 재분배가 전혀 없습니다.** 세 테이블이 조인 키로 동일하게 파티셔닝돼 있어, 각 서버가 대응 파티션 집합만 로컬로 조인합니다.
2. **재분배 여부는 조인 입력의 `PX SEND` 유무로 판별**합니다. Id 7·8·9 위에 SEND가 없고 모두 같은 PX PARTITION HASH ALL(Id 4) 아래에 있습니다.
3. **집계용 재분배도 여기선 없습니다.** Id 3 HASH GROUP BY의 키가 파티션 키(계약번호)와 같아 서버 로컬로 끝나므로, TQ가 Q1,00 하나뿐이고 조인 위에 SEND HASH가 붙지 않습니다.
4. **partial PWJ·hash-hash·broadcast는 조인 입력에 `PX SEND PARTITION (KEY)`/`PX SEND HASH`/`PX SEND BROADCAST`가 있어야** 성립합니다. 이 플랜의 조인 입력엔 어느 SEND도 없습니다 — 분배 방식을 뒤바꾼 값스왑 오답입니다.

📌 한 줄 정리: 사용량집계·공급계약·단가적용이 계약번호로 동일하게 64 해시 파티셔닝돼 조인 입력 Id 7·8·9가 같은 PX PARTITION HASH ALL 아래에서 SEND 없이 대응 파티션 집합만 조인하고 집계 키까지 파티션 키와 같으므로, 재분배가 없는 full 파티션 와이즈 조인이다.
