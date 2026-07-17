<!--meta
번호: 1
대상장: 1
대상절: 1.3
절제목: 액세스 방식과 블록 I/O
문제유형: 적절하지_않은_것
보조자료: 없음
DBMS: 오라클
정답: 1
선택지유형: 서술형
함정유형: [정반대_진술]
대상개념: [Random_액세스, Sequential_액세스]
자극물밀도: 없음
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 1

### 문제

Sequential 액세스와 Random 액세스, 그리고 그에 동반되는 블록 단위 I/O에 대한 설명으로 가장 적절하지 <u>않은</u> 것은?

### 선택지

① 인덱스를 경유해 테이블을 액세스할 때는 ROWID가 가리키는 블록들이 대체로 인접해 있어, 한 번의 I/O Call로 여러 블록을 함께 읽어 들이는 Multiblock I/O가 사용된다.
② Full Table Scan은 세그먼트에 속한 익스텐트 내 블록들을 물리적으로 저장된 순서대로 훑어 나가는 Sequential 액세스이며, 이때 Multiblock I/O가 동반된다.
③ `db file sequential read` 대기 이벤트는 이름과 달리 한 번에 한 블록씩 읽어 들이는 Single Block I/O 도중에 발생하며, 주로 인덱스 기반 Random 액세스에서 나타난다.
④ 인덱스 리프 블록을 논리적 연결 순서에 따라 좌에서 우로 스캔하는 것은 Sequential 액세스이며, 스캔 범위가 넓을수록 읽는 리프 블록 수가 늘어난다.

---

### 정답 — ①

### 왜 ①인가

두 액세스 방식을 그 **본질**부터 갈라놓고 봅니다.

- **Sequential 액세스**: 논리적으로든 물리적으로든 서로 연결된 순서를 따라 **차례로** 읽어 나가는 방식입니다. 인덱스 리프 블록을 순서대로 훑는 것(논리적 순서), Full Table Scan이 익스텐트 내 블록을 순서대로 훑는 것(물리적 순서)이 여기에 해당합니다.
- **Random 액세스**: 한 건을 얻기 위해 연결 순서와 무관한 위치를 **그때그때 찾아가는** 방식입니다. 인덱스에서 얻은 ROWID로 테이블의 특정 블록 하나를 집어 읽는 것이 대표적입니다.

여기에 I/O 단위가 짝지어집니다.

- Sequential 액세스로 대량 블록을 훑을 때는 인접 블록을 한꺼번에 읽는 **Multiblock I/O**(`db file scattered read`)가 유리합니다.
- Random 액세스는 흩어진 한 블록씩을 집어야 하므로 **Single Block I/O**(`db file sequential read`)로 처리됩니다.

①은 이 짝을 **정반대로** 이어 붙였습니다. 인덱스를 경유한 테이블 액세스는 ROWID가 가리키는 블록이 **서로 인접하리라는 보장이 없고**(그 인접 정도를 수치화한 것이 바로 클러스터링 팩터입니다), 한 건마다 블록 하나를 임의로 찾아가는 **Random 액세스 + Single Block I/O**입니다. "인접해서 Multiblock으로 읽는다"는 서술은 Full Scan의 성질을 인덱스 액세스에 잘못 옮겨 붙인 것입니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | **✗** | 인덱스 경유 테이블 액세스는 ROWID로 블록을 임의로 찾아가는 Random 액세스·Single Block I/O입니다. 블록이 인접해 Multiblock으로 읽는다는 것은 방향을 뒤집은 서술입니다 |
| ② | ○ | Full Table Scan은 익스텐트 내 블록을 물리적 순서대로 읽는 Sequential 액세스이고, 인접 블록을 묶어 읽는 Multiblock I/O가 동반됩니다 |
| ③ | ○ | `db file sequential read`는 이름과 달리 한 번에 한 블록을 읽는 Single Block I/O 중 발생하며, 인덱스 Random 액세스가 그 전형입니다 |
| ④ | ○ | 인덱스 리프 블록을 논리적 순서로 좌에서 우로 훑는 것은 Sequential 액세스이고, 스캔 범위가 넓을수록 읽는 리프 블록 수가 증가합니다 |

---

## ✅ 이 문제의 핵심

1. **Sequential = 연결된 순서를 차례로**, **Random = 순서 무관한 위치를 그때그때** 찾아가기. 방식이 먼저 정해지고 I/O 단위가 따라옵니다.
2. **Sequential ↔ Multiblock I/O(`scattered read`)**, **Random ↔ Single Block I/O(`sequential read`)** — 대기 이벤트 이름이 직관과 반대라 헷갈리기 쉽습니다.
3. 인덱스 경유 테이블 액세스는 Random·Single Block입니다. 그 블록들이 얼마나 인접했는지를 재는 지표가 **클러스터링 팩터**입니다.
4. Full Table Scan은 Sequential·Multiblock으로, 넓은 범위를 대량으로 훑을 때 유리합니다.

📌 한 줄 정리: 인덱스로 테이블을 읽는 것은 순서 무관한 위치를 한 블록씩 찾아가는 Random·Single Block I/O이지, 인접 블록을 한꺼번에 읽는 Multiblock I/O가 아닙니다.
