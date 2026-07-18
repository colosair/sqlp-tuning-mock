<!--meta
번호: 8
대상장: 3
대상절: 3.3
절제목: 인덱스 스캔 효율화
문제유형: 적절하지_않은_것
보조자료: 없음
DBMS: 공통
정답: 4
선택지유형: 서술형
함정유형: [정반대_진술]
대상개념: [Index_Fast_Full_Scan, 인덱스_전용_스캔, Index_Full_Scan]
자극물밀도: 없음
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 8

### 문제

인덱스만 읽고 끝내는 인덱스 전용 스캔(커버링)과, 인덱스 전체를 읽는 두 방식 — Index Full Scan과 Index Fast Full Scan — 에 대한 설명으로 가장 적절하지 <u>않은</u> 것은?

### 선택지

① 인덱스 전용 스캔(커버링)은 쿼리가 참조하는 컬럼이 인덱스 안에 모두 들어 있을 때 테이블(TABLE ACCESS BY INDEX ROWID)을 되짚지 않고 인덱스만 읽어 결과를 내는 것으로, ROWID로 테이블 블록을 임의 접근하는 Random 액세스를 없애 조회 부담을 던다.

② 선두 컬럼에 걸 조건이 없어 Range Scan을 쓰지 못하더라도, 조회에 필요한 컬럼이 인덱스에 다 있으면 옵티마이저는 인덱스 전체를 리프 연결 순서로 훑는 Index Full Scan으로 테이블을 건드리지 않고 처리할 수 있다.

③ Index Fast Full Scan은 인덱스 세그먼트를 리프의 논리적 연결이 아니라 물리적 저장 순서대로 Multiblock I/O로 읽어 대량 처리에 유리하고 병렬로도 수행되지만, 결과가 인덱스 키 순서로 정렬되어 나오지는 않는다.

④ Index Fast Full Scan은 리프 블록을 논리적 연결 순서를 따라 한 블록씩 Single Block I/O로 읽어 결과가 인덱스 키 순서로 정렬되고, Index Full Scan은 세그먼트를 물리적 저장 순서로 Multiblock I/O로 읽어 정렬을 보장하지 않는다.

---

### 정답 — ④

### 왜 ④인가

인덱스 전체를 읽는 두 방식은 **읽는 순서·I/O 단위·정렬 보장**이 정확히 반대입니다. 이름이 비슷해 헷갈리지만 성질은 대칭입니다.

```text
                 읽는 순서            I/O 단위        키 순서 정렬   병렬
--------------------------------------------------------------------------
Index Full Scan  리프 논리적 연결순서  Single Block    보장 O        보통 X
Index Fast Full  세그먼트 물리적 순서  Multiblock      보장 X        가능

정렬이 필요한 쿼리 → Index Full Scan (키 순서 유지 → ORDER BY 대체)
대량을 빨리 훑기   → Index Fast Full Scan (Multiblock·병렬, 순서는 깨짐)
```

④는 이 두 방식의 성질을 **통째로 맞바꿔** 놓았습니다. 리프의 논리적 연결 순서를 Single Block으로 따라가며 키 순서를 유지하는 것은 **Index Full Scan**이고, 세그먼트를 물리적 순서대로 Multiblock으로 읽어 정렬이 깨지는 것은 **Index Fast Full Scan**입니다. ④는 이 둘의 설명을 서로 바꿔 붙였으므로 정반대 서술입니다.

①·②·③은 옳습니다. 커버링으로 테이블 Random 액세스를 없애는 원리(①), 선두 컬럼 조건이 없어도 커버링이면 Index Full Scan으로 처리 가능한 점(②), Index Fast Full Scan의 물리적·Multiblock·병렬 성질과 정렬 미보장(③)이 모두 두 스캔의 실제 동작에 부합합니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ○ | 참조 컬럼이 인덱스에 다 들어 있으면 테이블을 되짚지 않고 인덱스만 읽어, ROWID 기반 테이블 Random 액세스를 제거합니다 |
| ② | ○ | 선두 컬럼 조건이 없어 Range Scan을 못 써도, 필요한 컬럼이 인덱스에 있으면 Index Full Scan으로 테이블 액세스 없이 처리할 수 있습니다 |
| ③ | ○ | Index Fast Full Scan은 세그먼트를 물리적 순서로 Multiblock·병렬로 읽어 대량 처리에 유리하되, 결과가 키 순서로 정렬되지는 않습니다 |
| ④ | **✗** | 논리적 연결 순서·Single Block·키 순서 정렬은 Index Full Scan의 성질이고, 물리적 순서·Multiblock·정렬 미보장은 Index Fast Full Scan의 성질입니다. 둘의 설명을 서로 맞바꾼 정반대 서술입니다 |

---

## ✅ 이 문제의 핵심

1. **Index Full Scan = 리프 논리적 순서·Single Block·키 순서 정렬(ORDER BY 대체 가능)**.
2. **Index Fast Full Scan = 세그먼트 물리적 순서·Multiblock·병렬, 대신 정렬은 깨짐**.
3. 두 방식의 **읽는 순서·I/O 단위·정렬 보장은 서로 반대**입니다. 맞바꾸면 오답입니다.
4. **커버링(인덱스 전용 스캔)** 은 참조 컬럼이 인덱스에 다 있을 때 테이블 Random 액세스를 제거합니다.

📌 한 줄 정리: 리프 논리적 순서로 Single Block·정렬 유지하는 것은 Index Full Scan, 물리적 순서로 Multiblock·정렬이 깨지는 것은 Index Fast Full Scan인데, 두 설명을 서로 맞바꾼 ④는 정반대 서술입니다.
