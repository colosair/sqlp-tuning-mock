<!--meta
번호: 8
대상장: 3
대상절: 3.3
절제목: 인덱스 스캔 효율화
문제유형: 적절하지_않은_것
보조자료: 없음
DBMS: 공통
정답: 2
선택지유형: 서술형
함정유형: [정반대_진술]
대상개념: [Index_Full_Scan, Index_Fast_Full_Scan, 인덱스_스캔_효율]
자극물밀도: 없음
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 8

### 문제

Index Full Scan과 Index Fast Full Scan, 그리고 테이블 액세스 없이 인덱스만 읽고 끝나는 스캔에 대한 설명으로 가장 적절하지 <u>않은</u> 것은?

### 선택지

① Index Full Scan은 인덱스 리프 블록을 논리적 연결 순서를 따라 한 블록씩 Single Block I/O로 끝까지 훑으므로, 인덱스 키 순서로 정렬된 결과를 얻을 수 있어 `ORDER BY`를 대체해 소트를 생략할 수 있다.

② Index Fast Full Scan은 인덱스 리프 블록의 논리적 연결 순서를 따라 읽으므로 결과가 인덱스 키 순서로 정렬되어 나오고, 그 덕분에 `ORDER BY`를 소트 없이 대체할 수 있다.

③ 쿼리가 필요로 하는 컬럼이 인덱스 안에 모두 들어 있으면, 어느 방식으로 스캔하든 테이블 액세스(TABLE ACCESS BY INDEX ROWID)를 생략하고 인덱스만 읽어 결과를 낼 수 있다.

④ Index Fast Full Scan은 인덱스 세그먼트 전체를 물리적 저장 순서대로 Multiblock I/O로 읽어 대량 스캔에 유리하고, 병렬로도 수행할 수 있다.

---

### 정답 — ②

### 왜 ②인가

두 스캔은 **읽는 순서**가 다르고, 그 차이가 정렬 보장 여부를 가릅니다.

```text
Index Full Scan
   읽는 순서 : 리프 블록의 논리적 연결 순서 (인덱스 키 순서)
   I/O       : 한 블록씩 Single Block I/O
   정렬      : 인덱스 키 순서 보장 → ORDER BY 소트 생략 가능

Index Fast Full Scan
   읽는 순서 : 세그먼트의 물리적 저장 순서 (연결 순서 무시)
   I/O       : 인접 블록을 묶는 Multiblock I/O, 병렬 가능
   정렬      : 키 순서 보장 안 됨 → ORDER BY 소트 생략 불가
```

②는 이 관계를 **정반대로** 진술했습니다. 인덱스 키 순서로 정렬된 결과를 주는 것은 **Index Full Scan**입니다. Index Fast Full Scan은 리프 블록을 논리적 연결 순서가 아니라 **물리적 저장 순서**로 훑기 때문에 결과가 키 순서로 나오지 않으며, 그래서 `ORDER BY`를 소트 없이 대체할 수 없습니다. 정렬 보장을 두 스캔 사이에서 맞바꿔 붙인 서술입니다.

①·④·③은 옳습니다. Index Full Scan의 Single Block·키 순서 보장(①), Index Fast Full Scan의 Multiblock·병렬 스캔(④), 그리고 필요한 컬럼이 인덱스에 다 있을 때의 인덱스 전용 스캔(테이블 액세스 생략, ③)이 두 스캔의 성질에 부합합니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ○ | Index Full Scan은 리프 블록을 논리적 연결 순서로 Single Block I/O로 훑어 키 순서 결과를 주므로 `ORDER BY` 소트를 생략할 수 있습니다 |
| ② | **✗** | 방향이 뒤집혔습니다. 키 순서 정렬을 보장하는 것은 Index Full Scan이고, Fast Full Scan은 물리적 순서로 읽어 정렬을 보장하지 못해 `ORDER BY`를 대체할 수 없습니다 |
| ③ | ○ | 필요한 컬럼이 인덱스에 다 있으면 어느 방식이든 테이블 액세스를 생략하고 인덱스만 읽어 결과를 낼 수 있습니다(인덱스 전용 스캔) |
| ④ | ○ | Index Fast Full Scan은 세그먼트를 물리적 순서대로 Multiblock I/O로 읽어 대량 스캔에 유리하고 병렬 수행이 가능합니다 |

---

## ✅ 이 문제의 핵심

1. **Index Full Scan = 논리적 연결 순서·Single Block I/O·키 순서 보장.** `ORDER BY` 소트를 생략할 수 있습니다.
2. **Index Fast Full Scan = 물리적 저장 순서·Multiblock I/O·병렬 가능·정렬 미보장.** 대량 스캔엔 빠르지만 순서를 못 줍니다.
3. 정렬이 필요하면 Index Full Scan, 순서가 필요 없는 대량 처리면 Index Fast Full Scan — 정렬 보장 여부가 갈림길입니다.
4. 필요한 컬럼이 인덱스에 다 있으면 **테이블 액세스를 생략**하는 인덱스 전용 스캔이 되고, 이는 어느 방식에서든 가능합니다.

📌 한 줄 정리: 인덱스 키 순서로 정렬된 결과를 주어 `ORDER BY`를 대체하는 것은 Index Full Scan이며, 물리적 순서로 읽는 Index Fast Full Scan은 정렬을 보장하지 못합니다.
