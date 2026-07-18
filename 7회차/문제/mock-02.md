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
대상개념: [Direct_Path_IO, Wait_Time, Multiblock_IO]
자극물밀도: 없음
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 2

### 문제

버퍼 캐시(SGA)를 우회해 디스크와 PGA 사이에서 곧바로 오가는 Direct Path I/O(`direct path read`·`direct path write`)와, 그때 관측되는 대기 이벤트에 대한 설명으로 가장 적절한 것은?

### 선택지

① Direct-Path Insert(`/*+ append */`)처럼 데이터를 고수위선(HWM) 위 새 블록에 곧바로 써 넣는 작업도, 기록에 앞서 그 블록을 버퍼 캐시에 올렸다가 DBWR가 내려쓰는 경로를 거치므로 일반 INSERT와 다를 바 없는 버퍼 캐시 경유 쓰기다.

② 여러 블록을 한 번의 I/O Call로 묶어 읽는 Multiblock I/O는 버퍼 캐시를 경유하는 경우에만 성립하는 개념이라, 버퍼 캐시를 우회하는 Direct Path Read는 블록을 하나씩만 집어 오는 Single Block I/O로 처리된다.

③ 정렬이나 해시 조인의 작업 영역이 PGA에 다 담기지 못해 임시 테이블스페이스로 내려썼다가 되읽을 때는 버퍼 캐시를 우회하는 Direct Path I/O가 쓰이며, 내려쓰는 단계에서는 `direct path write temp` 대기 이벤트가 관측된다.

④ Full Table Scan을 직렬로 수행할 때는 버퍼 캐시를 경유하는 Multiblock I/O만 쓰이고, 버퍼 캐시를 우회하는 Direct Path Read는 병렬 쿼리에서만 나타나므로 직렬 Full Scan에서는 발동하지 않는다.

---

### 정답 — ③

### 왜 ③인가

Direct Path I/O는 **버퍼 캐시(SGA)를 거치지 않고** 디스크와 수행 프로세스의 PGA 사이에서 블록을 곧바로 주고받는 경로입니다. 읽기와 쓰기 양쪽에 다 있고, 각기 다른 대기 이벤트로 관측됩니다.

```text
경로              방향   버퍼 캐시   대표 대기 이벤트
--------------------------------------------------------------
Direct Path Read  읽기   우회        direct path read
                                     (임시영역 되읽기: direct path read temp)
Direct Path Write 쓰기   우회        direct path write
                                     (정렬/해시 스필: direct path write temp)

정렬·해시 작업영역이 PGA를 넘침
  → 임시 테이블스페이스로 '내려쓰기' = direct path write temp
  → 뒤에 다시 '되읽기'            = direct path read temp
```

③은 이 관계를 정확히 짚었습니다. 정렬·해시 조인의 워크에어리어가 PGA에 다 못 담기면 임시 테이블스페이스로 스필하는데, 이 스필 I/O는 캐시를 우회하는 Direct Path I/O이고 내려쓰는 단계에서 `direct path write temp` 대기가 잡힙니다.

나머지는 모두 Direct Path의 **동작 경계를 뭉갠** 서술입니다. ①은 캐시를 우회하는 Direct-Path Insert를 캐시 경유 쓰기로, ②는 캐시 우회 읽기를 Single Block으로만, ④는 Direct Path Read를 병렬 전용으로 좁혔습니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ✗ | Direct-Path Insert는 버퍼 캐시를 우회해 HWM 위 새 블록에 곧바로 기록합니다. "캐시에 올렸다가 DBWR가 내려쓴다"는 것은 일반(conventional) 경로와의 경계를 뭉갠 서술입니다 |
| ② | ✗ | Direct Path Read도 인접한 여러 블록을 한 Call에 묶어 읽는 Multiblock I/O입니다. 다만 그 블록을 캐시가 아닌 PGA로 적재할 뿐이며, Single Block으로 처리되는 것이 아닙니다 |
| ③ | **○** | 정렬·해시 작업영역이 PGA를 넘쳐 임시 테이블스페이스로 스필할 때는 캐시를 우회하는 Direct Path I/O가 쓰이고, 내려쓰기 단계에서 `direct path write temp` 대기가 관측됩니다 |
| ④ | ✗ | Direct Path Read는 병렬 쿼리 전용이 아닙니다. 직렬 수행이라도 큰 세그먼트를 훑을 때는 직렬 Direct Path Read가 발동할 수 있어, "직렬 Full Scan에서는 안 나온다"는 경계는 틀립니다 |

---

## ✅ 이 문제의 핵심

1. **Direct Path I/O = 버퍼 캐시 우회**, 디스크↔PGA 직행 경로입니다. 읽기·쓰기 모두 존재합니다.
2. **정렬·해시 스필**은 임시 테이블스페이스로의 Direct Path Write이며, 내려쓰기는 `direct path write temp`로 잡힙니다.
3. **Direct Path Read도 Multiblock**입니다. 여러 블록을 한 Call에 묶되 캐시 대신 PGA로 적재할 뿐입니다.
4. **Direct-Path Insert는 HWM 위에 직접 기록**하고, **직렬 Full Scan도 Direct Path Read가 발동**할 수 있어 병렬 전용이 아닙니다.

📌 한 줄 정리: Direct Path I/O는 캐시를 우회하는 읽기·쓰기 경로이고 정렬·해시 스필의 임시영역 쓰기는 `direct path write temp`로 관측되는데, 이를 캐시 경유·Single Block·병렬 전용으로 좁힌 서술들은 Direct Path의 동작 경계를 뭉갠 것입니다.
