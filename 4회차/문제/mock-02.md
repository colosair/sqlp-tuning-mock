<!--meta
번호: 2
대상장: 1
대상절: 1.3
절제목: 데이터베이스 I/O 메커니즘
문제유형: 적절한_것
보조자료: 없음
DBMS: 오라클
정답: 3
선택지유형: 서술형
함정유형: [경계_오해]
대상개념: [Multiblock_IO, Direct_Path_IO, 대기_이벤트]
자극물밀도: 없음
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 2

### 문제

대량 스캔 시의 두 가지 I/O 경로 — 버퍼 캐시(SGA)를 경유하는 Multiblock I/O와 그것을 우회하는 Direct Path Read — 와 그때 관측되는 대기 이벤트에 대한 설명으로 가장 적절한 것은?

### 선택지

① Full Table Scan의 Multiblock I/O든 병렬 쿼리의 Direct Path Read든 읽어 들인 블록은 버퍼 캐시에 적재되어 다른 세션이 재활용할 수 있고, 대기 이벤트도 둘 다 `db file scattered read`로 동일하게 관측된다.

② Direct Path Read는 서버 프로세스가 디스크 블록을 버퍼 캐시에 먼저 올린 뒤 자신의 PGA로 복사하는 방식이라, 캐시에 해당 블록의 더티 버퍼가 남아 있으면 그것을 그대로 읽어 디스크 접근을 건너뛴다.

③ Direct Path Read는 읽은 블록을 버퍼 캐시(SGA)를 거치지 않고 프로세스의 PGA로 곧바로 적재하며, 이때 관측되는 대기 이벤트는 `db file scattered read`가 아니라 `direct path read`다.

④ 병렬 쿼리로 대량 세그먼트를 훑을 때는 블록을 캐시에 두고 공유하는 편이 유리하므로, 오라클은 병렬 Full Scan을 Direct Path Read가 아니라 버퍼 캐시를 경유하는 Multiblock I/O로 처리하는 것을 기본으로 삼는다.

---

### 정답 — ③

### 왜 ③인가

대량 스캔에는 **캐시를 거치는 경로**와 **캐시를 우회하는 경로**가 따로 있고, 대기 이벤트도 갈립니다. 이 경계를 뭉개면 안 됩니다.

```text
버퍼 캐시 경유 Multiblock I/O
   경로 : 디스크 → 버퍼 캐시(SGA) → 서버 프로세스
   대기 : db file scattered read
   전형 : (직렬) Full Table Scan, Index Fast Full Scan

Direct Path Read (캐시 우회)
   경로 : 디스크 → 프로세스 PGA  (SGA 버퍼 캐시를 거치지 않음)
   대기 : direct path read
   전형 : 병렬 쿼리 스캔, 대량 세그먼트 스캔
   전제 : 대상 세그먼트의 더티 버퍼를 먼저 디스크로 내리는 체크포인트 수행
```

③은 Direct Path Read의 본질을 정확히 짚었습니다. 읽은 블록을 **SGA 버퍼 캐시에 두지 않고 곧바로 PGA로** 가져오며, 그래서 대기 이벤트도 `db file scattered read`가 아니라 **`direct path read`** 로 관측됩니다.

나머지는 두 경로의 경계를 흐렸습니다.

- ①은 Direct Path Read까지 "버퍼 캐시에 적재되고 `scattered read`로 관측된다"고 묶었지만, Direct Path Read는 캐시를 우회하며 이벤트도 `direct path read`입니다.
- ②는 Direct Path Read가 캐시의 더티 버퍼를 재활용한다고 했으나, 실제로는 그 반대입니다. Direct Path로 읽기 전에 대상 세그먼트의 더티 버퍼를 **디스크로 내리는 체크포인트**를 먼저 수행한 뒤 디스크에서 직접 읽습니다. 캐시 블록을 활용하는 것이 아니라 비워 내는 것입니다.
- ④는 병렬 Full Scan의 기본 경로를 반대로 봤습니다. 병렬 슬레이브의 대량 스캔은 캐시 오염을 피하려 **Direct Path Read를 기본**으로 씁니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ✗ | Direct Path Read는 버퍼 캐시를 우회하고 대기 이벤트도 `direct path read`입니다. 두 경로를 `scattered read`·캐시 적재로 통일한 것은 경계를 뭉갠 서술입니다 |
| ② | ✗ | Direct Path Read는 읽기 전에 대상 세그먼트의 더티 버퍼를 디스크로 내린 뒤 직접 읽습니다. 캐시의 더티 버퍼를 재활용해 디스크를 건너뛴다는 것은 방향이 반대입니다 |
| ③ | **○** | Direct Path Read는 SGA를 거치지 않고 PGA로 직접 적재하며, 대기 이벤트는 `db file scattered read`가 아니라 `direct path read`입니다. 경로와 이벤트가 정확합니다 |
| ④ | ✗ | 병렬 Full Scan은 캐시 오염을 피해 Direct Path Read를 기본 경로로 씁니다. Multiblock I/O(캐시 경유)를 기본이라 한 것은 병렬 스캔의 경로를 뒤집은 서술입니다 |

---

## ✅ 이 문제의 핵심

1. **Multiblock I/O(캐시 경유) ↔ `db file scattered read`**, **Direct Path Read(캐시 우회) ↔ `direct path read`**. 대기 이벤트가 경로를 가릅니다.
2. Direct Path Read는 블록을 **SGA가 아니라 PGA**로 직접 가져옵니다 — 캐시 재활용이 아니라 캐시 우회입니다.
3. Direct Path로 읽기 전, 대상 세그먼트의 더티 버퍼를 **먼저 디스크로 내리는 체크포인트**가 선행됩니다.
4. **병렬 Full Scan의 기본 경로는 Direct Path Read**입니다 — 캐시 경유 Multiblock이 아닙니다.

📌 한 줄 정리: 대량 스캔에서 캐시를 우회해 PGA로 직접 읽는 Direct Path Read의 대기 이벤트는 `direct path read`이며, `scattered read`(캐시 경유 Multiblock)와 같은 경로로 묶으면 안 됩니다.
