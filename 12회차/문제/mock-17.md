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
자극물밀도: 실행계획_병렬_18행
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 17

### 문제

조달청 납품 정산 야간 배치가 `납품이행실적`(약 2억 6천만 건)을 **업체코드로 `공급업체`(약 5,200건)와, 품목코드로 `조달품목`(약 90만 건)과** 각각 조인해 업체·품목분류별 납품 건수를 집계한다. 세 테이블 어느 쪽도 조인 키 기준 파티션이 아니다. 아래 병렬 실행계획에서 **두 조인이 병렬 서버(Slave) 사이에 각각 어떤 분배 방식으로 수행되는지** 직접 지목한 설명으로 가장 적절한 것은?

#### [아 래]

```text
| Id  | Operation                     | Name         | TQ    |IN-OUT|
|-----|-------------------------------|--------------|-------|------|
|   0 | SELECT STATEMENT              |              |       |      |
|   1 |  PX COORDINATOR               |              |       |      |
|   2 |   PX SEND QC (RANDOM)         | :TQ10003     | Q1,03 | P->S |
|   3 |    HASH GROUP BY              |              | Q1,03 | PCWP |
|*  4 |     HASH JOIN                 |              | Q1,03 | PCWP |
|   5 |      PX RECEIVE               |              | Q1,03 | PCWP |
|   6 |       PX SEND HASH            | :TQ10002     | Q1,02 | P->P |
|*  7 |        HASH JOIN              |              | Q1,02 | PCWP |
|   8 |         PX RECEIVE            |              | Q1,02 | PCWP |
|   9 |          PX SEND BROADCAST    | :TQ10000     | Q1,00 | P->P |
|  10 |           PX BLOCK ITERATOR   |              | Q1,00 | PCWC |
|* 11 |            TABLE ACCESS FULL  | 공급업체     | Q1,00 | PCWP |
|  12 |         PX BLOCK ITERATOR     |              | Q1,02 | PCWC |
|* 13 |          TABLE ACCESS FULL    | 납품이행실적 | Q1,02 | PCWP |
|  14 |      PX RECEIVE               |              | Q1,03 | PCWP |
|  15 |       PX SEND HASH            | :TQ10001     | Q1,01 | P->P |
|  16 |        PX BLOCK ITERATOR      |              | Q1,01 | PCWC |
|* 17 |         TABLE ACCESS FULL     | 조달품목     | Q1,01 | PCWP |
```

### 선택지

① 업체코드 조인(Id 7)은 조인 키의 해시로 공급업체와 납품이행실적을 양쪽 재분배하는 hash-hash이고, 품목코드 조인(Id 4)은 소형 조달품목을 복제하는 broadcast 분배다.

② 업체코드 조인(Id 7)에서 대형 납품이행실적(Id 13)을 `PX SEND BROADCAST`(Id 9)로 전 서버에 복제하고, 소형 공급업체(Id 11)는 자기 블록 범위만 읽어 조인하는 broadcast 분배다.

③ 업체코드 조인(Id 7)은 소형 공급업체(Id 11)를 `PX SEND BROADCAST`(Id 9)로 복제하고 납품이행실적(Id 13)은 재분배 없이 로컬로 읽는 broadcast이며, 품목코드 조인(Id 4)은 그 결과(Id 6)와 조달품목(Id 15)을 양쪽 `PX SEND HASH`로 재분배하는 hash-hash 분배다.

④ 두 조인이 다 broadcast 분배이며, 품목코드 조인(Id 4)에서도 조달품목이 Id 15에서 `PX SEND BROADCAST`로 복제된 뒤 로컬로 조인된다.

---

### 정답 — ③

### 왜 ③인가

분배 방식은 **각 조인 입력이 어떤 `PX SEND`를 거치는지**로 읽습니다. 두 조인의 입력을 각각 봅니다.

**업체코드 조인(Id 7)** — 두 입력의 SEND를 봅니다.

```text
Id 9  PX SEND BROADCAST :TQ10000 (Q1,00 → 전 서버 복제)  공급업체를 모든 서버에 뿌림
Id 11  TABLE ACCESS FULL 공급업체 (약 5,200건)            복제 대상 — 소형
Id 12 PX BLOCK ITERATOR (Q1,02 → SEND 없음)              납품이행실적을 제자리에서 읽음
Id 13  TABLE ACCESS FULL 납품이행실적 (약 2.6억 건)        재분배 안 함 — 대형
```

소형 `공급업체`(Id 11) 위에만 `PX SEND BROADCAST`(Id 9)가 있고, 대형 `납품이행실적`(Id 13)은 SEND 없이 `PX BLOCK ITERATOR`(Id 12)로 제자리 스캔합니다. 한쪽에만 BROADCAST가 붙고 다른 쪽은 SEND가 없는 이 조합이 **broadcast 분배**입니다.

**품목코드 조인(Id 4)** — 두 입력의 SEND를 봅니다.

```text
Id 6  PX SEND HASH :TQ10002 (Q1,02 → Q1,03)   업체코드 조인 결과를 품목코드 해시로 재분배
Id 15 PX SEND HASH :TQ10001 (Q1,01 → Q1,03)   조달품목을 품목코드 해시로 재분배
```

두 입력 위에 각각 `PX SEND HASH`가 있어, 양쪽을 조인 키(품목코드) 해시로 재분배한 뒤 각 서버가 자기 버킷만 조인합니다. 이것이 **hash-hash 분배**입니다.

```text
업체코드 조인(Id 7) : 소형 공급업체에만 SEND BROADCAST(Id 9), 대형은 SEND 없음  → broadcast
품목코드 조인(Id 4) : 양쪽(Id 6·Id 15)에 각각 SEND HASH                        → hash-hash
```

즉 **두 조인의 분배가 서로 다릅니다(broadcast + hash-hash)**. 이를 정확히 지목한 것이 ③입니다. 두 분배를 맞바꾼 ①, broadcast 방향(대형·소형)을 뒤집은 ②, hash-hash를 broadcast로 본 ④는 노드와 어긋납니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ✗ | 두 조인의 분배를 맞바꾼 진술입니다. 업체코드 조인(Id 7)은 소형 공급업체에만 BROADCAST(Id 9)가 붙은 broadcast이고, 품목코드 조인(Id 4)은 Id 6·Id 15 양쪽에 SEND HASH가 붙은 hash-hash입니다 — hash-hash와 broadcast를 서로 바꿔 놓았습니다 |
| ② | ✗ | `PX SEND BROADCAST`(Id 9)는 소형 공급업체(Id 11) 쪽에 붙어 있고, 대형 납품이행실적(Id 13)은 Id 12 `PX BLOCK ITERATOR`로 제자리 스캔합니다. 복제되는 테이블을 대형·소형으로 뒤바꾼 값스왑입니다 |
| ③ | **○** | 업체코드 조인은 소형 공급업체(Id 11)를 BROADCAST(Id 9)로 복제하고 대형 납품이행실적(Id 13)을 로컬로 읽는 broadcast, 품목코드 조인은 Id 6·Id 15 양쪽을 SEND HASH로 재분배하는 hash-hash로, 두 조인의 분배를 정확히 지목했습니다 |
| ④ | ✗ | 품목코드 조인의 조달품목(Id 15)은 `PX SEND BROADCAST`가 아니라 `PX SEND HASH`이고, 업체코드 조인 결과(Id 6)도 SEND HASH입니다. 양쪽이 해시로 재분배되는 hash-hash를 broadcast로 본 진술입니다 |

---

## ✅ 이 문제의 핵심

1. **분배 방식은 조인 입력마다 `PX SEND`의 유무·종류로 판별**합니다. 업체코드 조인은 소형 쪽(Id 9)에만 BROADCAST, 대형 쪽(Id 12)은 SEND 없음 → broadcast입니다.
2. **품목코드 조인은 양쪽(Id 6·Id 15)에 SEND HASH** — 조인 키 해시로 재분배해 각 서버가 자기 버킷만 조인하는 hash-hash입니다.
3. **한 플랜 안에서 조인마다 분배가 다를 수 있습니다.** 대형×소형(공급업체)은 broadcast, 대형 결과×중형(조달품목)은 hash-hash로 갈렸습니다.
4. **복제 방향과 분배 종류를 뒤바꾸면 오답**입니다. BROADCAST는 소형(Id 11) 쪽에 붙고, hash-hash는 양쪽에 SEND HASH가 붙습니다 — 이를 대형 복제(②)·분배 맞교환(①)·전부 broadcast(④)로 보면 노드와 어긋납니다.

📌 한 줄 정리: 업체코드 조인은 소형 공급업체(Id 11)를 `PX SEND BROADCAST`(Id 9)로 복제하고 납품이행실적(Id 13)은 로컬로 읽는 broadcast, 품목코드 조인은 결과(Id 6)와 조달품목(Id 15)을 양쪽 `PX SEND HASH`로 재분배하는 hash-hash로, 한 플랜에 두 분배가 함께 쓰였다.
