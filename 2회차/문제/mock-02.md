<!--meta
번호: 2
대상장: 1
대상절: 1.3
절제목: 데이터베이스 I/O 메커니즘
문제유형: 적절한_것
보조자료: 없음
DBMS: 오라클
정답: 1
선택지유형: 서술형
함정유형: [오라클↔SQLServer_뒤바꿈]
대상개념: [Multiblock_IO, Single_Block_IO, 대기_이벤트]
자극물밀도: 없음
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 2

### 문제

오라클의 블록 I/O 방식(Single Block I/O·Multiblock I/O)과 그때 관측되는 대기 이벤트의 짝으로 가장 적절한 것은?

### 선택지

① 인덱스를 경유해 얻은 ROWID로 테이블 블록을 하나씩 임의로 찾아 읽는 Single Block I/O가 진행되는 동안에는 `db file sequential read` 대기 이벤트가 관측된다.
② Full Table Scan처럼 인접한 여러 블록을 한 번의 I/O Call로 묶어 읽는 Multiblock I/O 도중에는 `db file sequential read` 대기 이벤트가 나타난다.
③ 오라클에서 대량 블록을 훑는 Multiblock I/O에 대응하는 대기 이벤트는 SQL Server가 쓰는 `PAGEIOLATCH_SH`이며, `db file scattered read`는 SQL Server의 Full Scan 대기 이벤트다.
④ `db file scattered read`는 이름 그대로 흩어진 블록을 한 번에 하나씩 임의로 읽는 방식에서 발생하며, 주로 인덱스 Range Scan의 테이블 액세스 단계에서 관측된다.

---

### 정답 — ①

### 왜 ①인가

I/O 방식과 대기 이벤트의 짝은 이렇게 고정되어 있습니다. **이벤트 이름이 직관과 반대**라 이 짝을 외워 두어야 합니다.

```text
Single Block I/O  (한 번에 한 블록, 임의 위치)
   → 대기 이벤트: db file sequential read
   → 전형: 인덱스 Random 액세스(ROWID로 테이블 블록 하나씩)

Multiblock I/O    (한 Call에 인접 블록 여러 개)
   → 대기 이벤트: db file scattered read
   → 전형: Full Table Scan, Index Fast Full Scan
```

①은 이 짝에 정확히 부합합니다. 인덱스에서 얻은 ROWID로 테이블 블록을 한 건씩 임의로 찾아 읽는 것은 **Single Block I/O**이고, 그동안 관측되는 이벤트가 바로 (이름과 달리) `db file sequential read`입니다.

나머지는 이벤트 이름을 반대 방식에 붙였거나(②④), 오라클 이벤트와 SQL Server 이벤트를 **서로 뒤바꿔**(③) 놓았습니다. `PAGEIOLATCH` 계열은 SQL Server의 I/O 대기 이벤트이고, `db file sequential/scattered read`는 오라클 고유의 이벤트입니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | **○** | ROWID로 테이블 블록을 한 건씩 임의로 읽는 것은 Single Block I/O이며, 그때 `db file sequential read`가 관측됩니다. 짝이 정확합니다 |
| ② | ✗ | Multiblock I/O(Full Scan)에서 발생하는 이벤트는 `db file scattered read`입니다. `sequential read`를 붙인 것은 이벤트 이름을 반대 방식에 옮긴 서술입니다 |
| ③ | ✗ | `PAGEIOLATCH_SH`는 SQL Server의 대기 이벤트이고 `db file scattered read`는 오라클 것입니다. 두 DBMS의 이벤트를 서로 뒤바꿔 놓았습니다 |
| ④ | ✗ | `db file scattered read`는 인접 블록을 묶어 읽는 Multiblock I/O(Full Scan)에서 발생합니다. "한 블록씩 임의로 읽는다"는 Single Block I/O의 성질을 잘못 붙인 서술입니다 |

---

## ✅ 이 문제의 핵심

1. **Single Block I/O ↔ `db file sequential read`**(인덱스 Random 액세스), **Multiblock I/O ↔ `db file scattered read`**(Full Scan). 이름이 직관과 반대입니다.
2. `sequential read`가 "한 블록씩", `scattered read`가 "여러 블록"이라는 점을 이름 뜻과 분리해 외워야 헷갈리지 않습니다.
3. `db file sequential/scattered read`는 오라클 이벤트, `PAGEIOLATCH` 계열은 SQL Server 이벤트입니다. 진영이 다릅니다.
4. 인덱스 Range Scan의 테이블 액세스 단계는 ROWID 기반 Random 액세스이므로 Single Block I/O(`sequential read`)로 처리됩니다.

📌 한 줄 정리: ROWID로 테이블을 한 블록씩 찾아 읽는 Single Block I/O에서 관측되는 이벤트는 `db file sequential read`이며, `scattered read`(Multiblock)와 SQL Server의 `PAGEIOLATCH`를 뒤섞으면 안 됩니다.
