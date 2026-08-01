<!--meta
번호: 17
대상장: 6
대상절: 6.5
절제목: 대용량 배치 프로그램 튜닝
문제유형: 직접지목형
보조자료: 실행계획
DBMS: 오라클
정답: 4
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

고속도로 통행료 정산 배치에서 `통행내역` 테이블(약 2억 4천만 건)과 `요금소` 테이블(약 1,500건)을 요금소코드로 병렬 해시 조인한 뒤 요금소코드별로 통행료를 집계한다. 두 테이블 모두 파티셔닝돼 있지 않다. 이 병렬 실행계획은 조인을 위해 두 테이블을 병렬 서버(Slave) 사이에 **어떻게 분배**하는가? 가장 정확히 지목한 것은?

#### [아 래]

```text
| Id  | Operation                  | Name       | TQ    |IN-OUT|
|-----|----------------------------|------------|-------|------|
|   0 | SELECT STATEMENT           |            |       |      |
|   1 |  PX COORDINATOR            |            |       |      |
|   2 |   PX SEND QC (RANDOM)      | :TQ10001   | Q1,01 | P->S |
|   3 |    HASH GROUP BY           |            | Q1,01 | PCWP |
|   4 |     PX RECEIVE             |            | Q1,01 | PCWP |
|   5 |      PX SEND HASH          | :TQ10000   | Q1,00 | P->P |
|   6 |       HASH GROUP BY        |            | Q1,00 | PCWP |
|*  7 |        HASH JOIN           |            | Q1,00 | PCWP |
|   8 |         TABLE ACCESS FULL  | 요금소      | Q1,00 | PCWP |
|   9 |         PX BLOCK ITERATOR  |            | Q1,00 | PCWC |
|* 10 |          TABLE ACCESS FULL | 통행내역    | Q1,00 | PCWP |
```

### 선택지

① 통행내역(2억 4천만 건)이 각 병렬 서버에 통째로 REPLICATE(복제)되어 Id 10에서 서버마다 전량이 읽히고, 요금소(1,500건)는 Id 9 `PX BLOCK ITERATOR`로 블록 범위를 나눠 병렬 스캔된다. 조인(Id 7)은 이렇게 갖춰진 두 입력으로 슬레이브 안에서 수행되고, Id 5 `PX SEND HASH`는 그 조인 결과를 상위로 넘기는 경로다.

② 한 병렬 서버가 요금소 1,500건을 읽어 Id 8 위의 `PX SEND BROADCAST`로 전 서버에 뿌리고, 통행내역은 Id 9 `PX BLOCK ITERATOR`로 재분배 없이 읽는 broadcast 방식이다. Id 5 `PX SEND HASH`의 :TQ10000이 그 브로드캐스트 경로이며, 큰 통행내역은 네트워크로 흐르지 않는다.

③ 요금소와 통행내역을 양쪽 다 요금소코드 해시로 재분배하는 hash-hash 방식이며, Id 5 `PX SEND HASH`가 :TQ10000으로 그 재분배를 수행하고 Id 4 `PX RECEIVE`가 Q1,01에서 받아 짝을 맞추므로, 두 테이블의 같은 요금소코드가 같은 슬레이브로 모인 뒤 Id 7에서 조인된다.

④ 요금소는 재분배도 브로드캐스트도 없이 각 병렬 서버가 자체적으로 전체를 Full Scan(Id 8)하는 REPLICATE 방식이고, 통행내역은 각 서버가 Id 9 `PX BLOCK ITERATOR`로 자기 블록 범위만 병렬 스캔(Id 10)한다. 조인은 재분배 없이 슬레이브 안에서 수행되며, Id 5 `PX SEND HASH`는 상위 HASH GROUP BY 재분배용이다.

---

### 정답 — ④

### 왜 ④인가

분배 방식은 **조인(Id 7)의 두 입력이 각각 어떤 경로로 조인 서버에 도달하는지**로 읽습니다. 핵심 신호는 조인 입력 바로 위에 `PX SEND`가 있느냐입니다.

```text
Id 7  HASH JOIN (Q1,00)                              슬레이브 집합 Q1,00 안에서 조인
Id 8   TABLE ACCESS FULL 요금소 (Q1,00, 위에 PX SEND 없음)  요금소: 각 서버가 스스로 전체 읽음 = REPLICATE
Id 9   PX BLOCK ITERATOR (Q1,00)                     통행내역: 블록 범위 분할
Id 10   TABLE ACCESS FULL 통행내역 (Q1,00)            재분배 없이 로컬 병렬 스캔
```

- 요금소(Id 8)는 1,500건에 불과합니다. 조인 입력 바로 위에 `PX SEND`(HASH도 BROADCAST도) 가 **아예 없습니다**. 이것이 **REPLICATE**의 표식으로, 각 병렬 서버가 요금소 전체를 **자체적으로 Full Scan**해 자기 메모리에 갖습니다. 한 서버가 읽어 다른 서버로 흘리는 broadcast와 달리 송신 오퍼레이션 자체가 없습니다.
- 통행내역(Id 10)은 파티셔닝돼 있지 않으므로, 각 서버가 Id 9 `PX BLOCK ITERATOR`로 **자기 블록 범위만** 병렬 스캔합니다. 역시 조인 입력 위에 `PX SEND`가 없어 **재분배가 없습니다**.
- 그 결과 조인(Id 7)은 재분배 없이 **슬레이브 안에서** 끝납니다. 유일한 재분배인 Id 5 `PX SEND HASH`는 조인이 아니라 그 위 **HASH GROUP BY**(부분집계 Id 6 → 집계 키로 재분배 → 최종집계 Id 3)를 위한 것입니다.

```text
④ REPLICATE : 요금소 = SEND 없음(각 서버 자체 Full Scan), 통행내역 = BLOCK ITERATOR 로컬 스캔  → Id 8·Id 10과 일치   ✔
① 역할 뒤바꿈 : 통행내역=REPLICATE, 요금소=BLOCK ITERATOR                                     → Id 8·Id 9와 반대(값 스왑)
② broadcast  : 요금소 위에 PX SEND BROADCAST                                       → 요금소(Id 8) 위엔 SEND 자체가 없음
③ hash-hash  : 양쪽 조인 입력 위에 PX SEND HASH                                 → Id 5 SEND HASH는 조인이 아닌 GROUP BY용
```

큰 테이블 통행내역(2억 4천만)을 네트워크로 흘리지 않고, 작은 요금소(1,500건)를 각 서버가 스스로 읽어 두는 것이 REPLICATE의 이점입니다. 따라서 ④가 옳습니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ✗ | REPLICATE되는 쪽과 블록 분할로 읽는 쪽을 뒤바꿨습니다. Id 9 `PX BLOCK ITERATOR`는 Id 10 통행내역 바로 위에 붙어 있으므로 블록 범위로 나뉘는 쪽이 통행내역이고, 서버마다 통째로 읽히는 쪽은 Id 8 요금소 1,500건입니다. 2억 4천만 건을 서버마다 복제하지는 않습니다 |
| ② | ✗ | broadcast라면 요금소 위에 `PX SEND BROADCAST`가 있어야 하는데, Id 8 요금소 위에는 `PX SEND`가 없습니다. Id 5 `PX SEND HASH`는 :TQ10000을 Q1,00에서 Q1,01로 보내는 상위 경로라 요금소를 뿌리는 통로가 될 수 없고, 각 서버가 스스로 읽는 REPLICATE입니다 |
| ③ | ✗ | hash-hash라면 두 조인 입력 Id 8·Id 10 위에 각각 `PX SEND HASH`가 있어야 하는데 거기엔 송신이 없습니다. Id 5 `PX SEND HASH`와 Id 4 `PX RECEIVE`는 조인(Id 7)보다 위, Id 6 부분집계와 Id 3 최종집계 사이에 있어 GROUP BY 재분배용입니다 |
| ④ | **○** | 요금소는 위에 `PX SEND`가 없어 각 서버가 자체 Full Scan하는 REPLICATE(Id 8), 통행내역은 `PX BLOCK ITERATOR`로 블록 범위 로컬 스캔(Id 10), 조인은 재분배 없이 슬레이브 안에서 수행 — Id 5 SEND HASH는 GROUP BY용이라는 지목이 플랜과 일치합니다 |

---

## ✅ 이 문제의 핵심

1. **REPLICATE는 작은 테이블을 각 서버가 자체적으로 전체 읽는 방식**입니다. 조인 입력 바로 위에 `PX SEND`가 없다는 것(Id 8)이 그 표식으로, broadcast·hash 재분배와 구분됩니다.
2. **재분배 여부는 조인 입력 위 `PX SEND` 유무로 판별**합니다. 요금소(Id 8)·통행내역(Id 10) 위에는 송신이 없어 조인이 슬레이브 안에서 재분배 없이 끝납니다.
3. **큰 테이블은 블록 범위 로컬 스캔.** 통행내역은 Id 9 `PX BLOCK ITERATOR`로 각 서버가 자기 블록만 읽어, 2억 4천만 건을 네트워크로 흘리지 않습니다.
4. **상단의 `PX SEND HASH`(Id 5)는 조인이 아니라 GROUP BY 재분배용**입니다. 이를 조인 재분배로 오해하면 hash-hash로 잘못 지목하게 됩니다.

📌 한 줄 정리: 요금소는 조인 입력 위에 `PX SEND`가 없어 각 서버가 스스로 전체를 읽는 REPLICATE(Id 8)이고 통행내역은 `PX BLOCK ITERATOR`로 블록 범위만 로컬 스캔(Id 10)하므로, 조인은 재분배 없이 슬레이브 안에서 수행되며 Id 5 `PX SEND HASH`는 상위 GROUP BY 재분배용입니다.
