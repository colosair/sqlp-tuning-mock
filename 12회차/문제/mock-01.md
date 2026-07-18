<!--meta
번호: 1
대상장: 1
대상절: 1.3
절제목: 데이터베이스 I/O 메커니즘
문제유형: 적절하지_않은_것
보조자료: 없음
DBMS: 오라클
정답: 1
선택지유형: 서술형
함정유형: [정반대_진술]
대상개념: [Multiblock_IO, Random_액세스, 대기_이벤트]
자극물밀도: 없음
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 1

### 문제

오라클이 데이터 블록을 읽는 두 방식인 한 블록씩 읽는 랜덤 액세스와 여러 블록을 한 번에 읽는 Multiblock I/O가 각각 어떤 대기 이벤트로 집계되고 무엇이 그 단위를 좌우하는지에 대한 설명으로 가장 적절하지 <u>않은</u> 것은?

### 선택지

① 인덱스를 경유해 ROWID로 테이블을 한 블록씩 찾아가는 랜덤 액세스는 읽은 블록들이 버퍼 캐시의 여러 슬롯에 흩어져 담기므로 `db file scattered read`로 대기하고, Full Table Scan처럼 인접한 여러 블록을 한 I/O Call로 요청하는 Multiblock I/O는 한 자리에 이어 담기므로 `db file sequential read`로 대기한다.

② 인덱스 수직 탐색이나 인덱스 경유 테이블 액세스처럼 한 번에 한 블록만 요청하는 Single Block I/O(랜덤 액세스)의 대기는 `db file sequential read`로 집계되며, 이 방식은 필요한 블록만 골라 읽는 대신 요청 횟수가 읽는 블록 수만큼 늘어난다.

③ Full Table Scan이나 Index Fast Full Scan처럼 인접한 여러 블록을 한 번의 I/O Call로 묶어 요청하는 Multiblock I/O의 대기는 `db file scattered read`로 집계되며, 한 Call로 요청하는 최대 블록 수는 `DB_FILE_MULTIBLOCK_READ_COUNT`의 상한을 따른다.

④ Multiblock I/O는 한 번의 Call이라 해도 익스텐트 경계를 넘어서까지 읽지는 않으며, 요청 범위 안에 이미 버퍼 캐시에 올라와 있는 블록이 끼어 있으면 그 지점에서 끊어 읽으므로 실제 한 Call의 블록 수가 `DB_FILE_MULTIBLOCK_READ_COUNT`보다 작아질 수 있다.

---

### 정답 — ①

### 왜 ①인가

두 대기 이벤트의 이름이 직관과 어긋나 반대로 붙기 쉽습니다. 어떤 방식이 어느 이벤트로 집계되는지를 갈라 봐야 합니다.

```text
Single Block I/O (랜덤 액세스)  : 한 번에 한 블록씩 요청
    → 인덱스 순서를 따라 순차적으로 한 블록씩 방문
    → 대기 이벤트 = db file sequential read

Multiblock I/O (Full Scan류)    : 인접한 여러 블록을 한 Call로 요청
    → 여러 블록이 버퍼 캐시의 흩어진 슬롯에 담김
    → 대기 이벤트 = db file scattered read
```

이벤트 이름은 **읽는 방식**이 아니라 **버퍼에 담기는 모습**에서 왔습니다. 한 블록씩 인덱스를 따라 순차적으로 읽는 랜덤 액세스가 `db file sequential read`, 여러 블록을 한 번에 읽어 캐시 슬롯에 흩뿌리는 Multiblock I/O가 `db file scattered read`입니다.

①은 이 둘을 **정반대로** 뒤집었습니다. 한 블록씩 찾아가는 랜덤 액세스를 `db file scattered read`로, 여러 블록을 묶어 읽는 Multiblock I/O를 `db file sequential read`로 서술했지만, 실제 집계는 그 반대입니다. 이벤트 이름의 유래(순차 방문 vs 흩어진 적재)를 읽기 단위와 어긋나게 맞바꾼 서술입니다.

②·③·④는 옳습니다. Single Block I/O가 `db file sequential read`로 집계된다는 점(②), Multiblock I/O가 `db file scattered read`이며 블록 수가 `DB_FILE_MULTIBLOCK_READ_COUNT`의 상한을 따른다는 점(③), 익스텐트 경계와 캐시 적중 블록 때문에 실제 Call 블록 수가 상한보다 작아질 수 있다는 점(④)이 모두 실제 I/O 동작에 부합합니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | **✗** | 한 블록씩 찾아가는 랜덤 액세스는 `db file sequential read`, 여러 블록을 한 Call로 읽는 Multiblock I/O는 `db file scattered read`로 집계됩니다. 두 이벤트 이름을 읽기 단위와 정반대로 맞바꾼 서술입니다 |
| ② | ○ | 인덱스 수직 탐색·인덱스 경유 테이블 액세스는 한 번에 한 블록만 요청하는 Single Block I/O로 `db file sequential read`로 대기하며, 요청 횟수가 읽는 블록 수만큼 늘어납니다 |
| ③ | ○ | Full Table Scan·Index Fast Full Scan의 Multiblock I/O는 `db file scattered read`로 집계되고, 한 Call 최대 블록 수는 `DB_FILE_MULTIBLOCK_READ_COUNT`의 상한을 따릅니다 |
| ④ | ○ | Multiblock I/O는 익스텐트 경계를 넘어 읽지 않고, 요청 범위에 캐시 적중 블록이 끼면 그 지점에서 끊으므로 실제 Call 블록 수가 상한보다 작아질 수 있습니다 |

---

## ✅ 이 문제의 핵심

1. **랜덤 액세스(Single Block I/O)**는 한 블록씩 인덱스를 따라 순차적으로 읽어 **`db file sequential read`**로 집계됩니다.
2. **Multiblock I/O**는 인접 여러 블록을 한 Call로 읽어 캐시 슬롯에 흩어 담으므로 **`db file scattered read`**로 집계됩니다.
3. 두 이벤트 이름은 읽기 방식이 아니라 **버퍼에 담기는 모습**에서 유래하므로 직관과 어긋나 맞바꾸기 쉽습니다.
4. Multiblock I/O의 한 Call 블록 수는 `DB_FILE_MULTIBLOCK_READ_COUNT`의 상한을 따르되, **익스텐트 경계와 캐시 적중 블록** 때문에 실제로는 그보다 작아질 수 있습니다.

📌 한 줄 정리: 한 블록씩 읽는 랜덤 액세스가 `db file sequential read`, 여러 블록을 한 번에 읽는 Multiblock I/O가 `db file scattered read`인데, 이 둘을 서로 바꾼 ①은 대기 이벤트를 읽기 단위와 정반대로 붙인 서술입니다.
