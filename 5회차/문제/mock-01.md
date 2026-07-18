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
대상개념: [Random_액세스, Sequential_액세스, Multiblock_IO]
자극물밀도: 없음
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 1

### 문제

Multiblock I/O가 한 번의 I/O Call로 읽어 들이는 블록 수, 그리고 그 반대편에 놓인 Single Block I/O·Random 액세스에 대한 설명으로 가장 적절하지 <u>않은</u> 것은?

### 선택지

① 한 번의 Multiblock I/O로 읽는 블록 수는 `DB_FILE_MULTIBLOCK_READ_COUNT`에 지정한 값과 같게 유지되며, 익스텐트 경계를 넘어가는지나 그 안에 이미 버퍼 캐시에 올라온 블록이 섞여 있는지는 이 개수를 바꾸지 못한다.

② Full Table Scan은 세그먼트의 블록을 물리적 저장 순서대로 훑어 나가는 Sequential 액세스이며, 인접한 여러 블록을 한 번에 읽어 들이는 Multiblock I/O가 동반되어 대기 이벤트는 `db file scattered read`로 나타난다.

③ 인덱스에서 얻은 ROWID로 테이블의 특정 블록 하나를 임의 위치에서 집어 오는 Random 액세스는 Single Block I/O로 처리되며, 그 대기 이벤트는 이름과 달리 `db file sequential read`이다.

④ `DB_FILE_MULTIBLOCK_READ_COUNT`를 크게 잡으면 같은 양의 블록을 훑을 때 한 Call에 묶이는 블록 수가 늘어 I/O Call 횟수가 줄어드는 경향이 있어, 넓은 범위를 훑는 Full Table Scan에 유리하게 작용할 수 있다.

---

### 정답 — ①

### 왜 ①인가

`DB_FILE_MULTIBLOCK_READ_COUNT`(이하 MBRC)는 한 번의 Multiblock I/O로 읽을 블록 수의 **상한**일 뿐, 매번 그 수만큼 읽는다는 뜻이 아닙니다. 실제로 한 Call에 묶이는 블록 수는 두 가지 경계에서 그보다 **줄어듭니다.**

```text
경계 1  익스텐트 : Multiblock I/O는 익스텐트 경계를 넘지 못한다.
                   익스텐트 끝에 MBRC보다 적은 블록만 남았으면 그만큼만 묶여 읽힌다.
경계 2  버퍼 캐시: 묶으려는 구간 중간에 이미 캐시에 올라온 블록이 있으면
                   그 지점에서 읽기가 끊겨, 앞·뒤로 조각난 더 작은 Call들로 나뉜다.
```

①은 이 관계를 **정반대로** 뒤집었습니다. "익스텐트 경계나 캐시 적재 여부와 무관하게 매번 MBRC만큼 읽는다"는 서술은, MBRC를 고정 개수로 오해한 것입니다. MBRC는 한 Call이 넘볼 수 있는 최대치를 정할 뿐이고, 익스텐트 끝과 이미 캐시에 있는 블록이 실제 묶음 크기를 그 아래로 깎습니다. 그래서 같은 Full Scan이라도 캐시 상태와 익스텐트 분할 정도에 따라 Call당 블록 수가 들쭉날쭉합니다.

②·③·④는 옳습니다. Full Scan의 Sequential·Multiblock·`scattered read`(②), 인덱스 경유 Random 액세스의 Single Block·`sequential read`(③), 그리고 MBRC를 키울 때의 I/O Call 절감 경향(④)이 모두 블록 I/O 메커니즘에 부합합니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | **✗** | MBRC는 한 Call의 블록 수 상한일 뿐입니다. 익스텐트 경계에서 끊기고 캐시에 있는 블록에서 조각나 실제 묶음은 그보다 작아지므로, "경계·캐시와 무관하게 그 수만큼 읽는다"는 방향을 뒤집은 서술입니다 |
| ② | ○ | Full Table Scan은 블록을 물리적 순서로 훑는 Sequential 액세스이고 Multiblock I/O가 동반되며 대기 이벤트는 `db file scattered read`입니다 |
| ③ | ○ | ROWID로 테이블 블록을 임의로 한 블록씩 집어 오는 Random 액세스는 Single Block I/O이고, 그 이벤트가 이름과 반대인 `db file sequential read`입니다 |
| ④ | ○ | MBRC를 키우면 한 Call에 묶이는 블록이 늘어 같은 블록 수를 읽을 때 I/O Call 횟수가 줄어드는 경향이 있어 대량 Full Scan에 유리할 수 있습니다 |

---

## ✅ 이 문제의 핵심

1. **MBRC는 한 Multiblock I/O Call의 블록 수 상한**이지 고정 개수가 아닙니다. 실제 묶음은 그보다 작아질 수 있습니다.
2. Multiblock I/O는 **익스텐트 경계를 넘지 못하고**, 구간 중간에 **이미 캐시에 있는 블록**을 만나면 거기서 끊겨 더 작은 Call로 조각납니다.
3. **Sequential(Full Scan) ↔ Multiblock I/O·`scattered read`**, **Random(인덱스 경유) ↔ Single Block I/O·`sequential read`** — 이벤트 이름이 직관과 반대입니다.
4. MBRC를 키우면 Call 횟수가 줄어드는 경향은 있지만, 캐시 상태·익스텐트 분할에 따라 Call당 블록 수는 일정하지 않습니다.

📌 한 줄 정리: `DB_FILE_MULTIBLOCK_READ_COUNT`는 한 Call의 블록 수 상한일 뿐, 익스텐트 경계와 캐시에 있는 블록이 실제 묶음을 그 아래로 깎으므로 "항상 그 수만큼 읽는다"는 서술은 방향을 뒤집은 것입니다.
