<!--meta
번호: 10
대상장: 4
대상절: 4.3
절제목: 조인 수행 원리
문제유형: 직접지목형
보조자료: 실행계획
DBMS: 오라클
정답: 3
선택지유형: 코드형
함정유형: [값스왑]
대상개념: [조인_방식_선택, 해시_조인, NL_조인]
자극물밀도: 실행계획_pipe_역공학
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 10

### 문제

채용 포털의 통계 배치가 `채용공고` 테이블(진행 중 공고 약 3만 건)과 `지원내역` 테이블(약 9,700만 건)을 공고번호로 조인해 채용직군별 접수 건수를 집계한다. 네 후보 SQL은 SELECT 목록·WHERE 조건·GROUP BY가 모두 같고, 조인 힌트만 서로 다르다. 아래 실행계획을 **낸** SQL로 가장 적절한 것은?

#### [아 래]

```text
| Id  | Operation             | Name       |
|-----|-----------------------|------------|
|   0 | SELECT STATEMENT      |            |
|   1 |  SORT GROUP BY        |            |
|*  2 |   HASH JOIN           |            |
|*  3 |    TABLE ACCESS FULL  | 채용공고    |
|*  4 |    TABLE ACCESS FULL  | 지원내역    |
```

### 선택지

① 아래 SQL
```sql
SELECT /*+ LEADING(a c) USE_HASH(c) */
       c.채용직군, COUNT(*)
  FROM 채용공고 c, 지원내역 a
 WHERE a.공고번호 = c.공고번호
   AND c.채용상태 = '진행중'
   AND a.지원상태 = '접수'
 GROUP BY c.채용직군;
```

② 아래 SQL
```sql
SELECT /*+ LEADING(c a) USE_NL(a) */
       c.채용직군, COUNT(*)
  FROM 채용공고 c, 지원내역 a
 WHERE a.공고번호 = c.공고번호
   AND c.채용상태 = '진행중'
   AND a.지원상태 = '접수'
 GROUP BY c.채용직군;
```

③ 아래 SQL
```sql
SELECT /*+ LEADING(c a) USE_HASH(a) */
       c.채용직군, COUNT(*)
  FROM 채용공고 c, 지원내역 a
 WHERE a.공고번호 = c.공고번호
   AND c.채용상태 = '진행중'
   AND a.지원상태 = '접수'
 GROUP BY c.채용직군;
```

④ 아래 SQL
```sql
SELECT /*+ LEADING(c a) USE_MERGE(a) */
       c.채용직군, COUNT(*)
  FROM 채용공고 c, 지원내역 a
 WHERE a.공고번호 = c.공고번호
   AND c.채용상태 = '진행중'
   AND a.지원상태 = '접수'
 GROUP BY c.채용직군;
```

---

### 정답 — ③

### 왜 ③인가

플랜을 세 가지 좌표 — **조인 방식, 빌드/프로브 순서, 액세스 방식** — 로 읽고, 힌트만 다른 네 SQL을 거꾸로 맞춥니다.

```text
Id 2  HASH JOIN            → 조인 방식은 해시 조인
Id 3  TABLE ACCESS FULL 채용공고   ← HASH JOIN의 첫(위) 자식 = Build Input(선행)
Id 4  TABLE ACCESS FULL 지원내역   ← HASH JOIN의 둘째(아래) 자식 = Probe Input(후행)
```

해시 조인에서 플랜의 **위쪽 자식이 Build Input**이고, 이는 조인 순서에서 **선행 테이블**입니다. 여기서는 채용공고(Id 3)가 Build, 지원내역(Id 4)이 Probe이고, 두 입력 모두 `TABLE ACCESS FULL`(인덱스 없이 전체 스캔)입니다. 이 세 가지를 동시에 만족하는 힌트는 **선행=채용공고(c) + 해시 조인**, 곧 `LEADING(c a) USE_HASH(a)`입니다.

```text
③ LEADING(c a) USE_HASH(a) : 선행 채용공고=Build(위), 지원내역=Probe(아래), 해시  → Id 2~4와 일치      ✔
① LEADING(a c) USE_HASH(c) : 선행 지원내역=Build → 위 자식이 지원내역이어야 함     → 플랜은 채용공고가 위
② LEADING(c a) USE_NL(a)   : NESTED LOOPS + 지원내역 인덱스 액세스                → 플랜은 HASH JOIN·FULL
④ LEADING(c a) USE_MERGE(a): MERGE JOIN + 양쪽 SORT JOIN                          → 플랜에 SORT JOIN 없음
```

- **①은 빌드/프로브가 뒤바뀝니다.** `LEADING(a c)`는 지원내역을 선행=Build로 지정하므로 HASH JOIN의 위 자식이 지원내역이어야 하는데, 플랜의 위 자식은 채용공고입니다.
- **②는 조인 방식이 다릅니다.** `USE_NL(a)`는 NESTED LOOPS를 만들고 후행 지원내역을 인덱스로 탐색합니다. 플랜의 `HASH JOIN`·양쪽 `TABLE ACCESS FULL`과 어긋납니다.
- **④도 조인 방식이 다릅니다.** `USE_MERGE(a)`는 소트 머지 조인이라 두 입력 위에 각각 `SORT JOIN` 노드가 생깁니다. 플랜엔 그 노드가 없습니다.

빌드 순서 하나(①), 조인 방식 둘(②·④)을 각각 플랜의 관측 가능한 노드로 배제하면, 이 플랜을 정확히 내는 것은 ③뿐입니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ✗ | `LEADING(a c)`가 지원내역을 선행=Build로 지정해 HASH JOIN의 위 자식이 지원내역이 됩니다. 플랜의 위 자식(Id 3)은 채용공고여서 빌드/프로브가 스왑된 SQL입니다 |
| ② | ✗ | `USE_NL(a)`는 NESTED LOOPS와 지원내역 인덱스 탐색을 만듭니다. 플랜은 Id 2 HASH JOIN에 양쪽이 TABLE ACCESS FULL이라 조인 방식이 다릅니다 |
| ③ | **○** | `LEADING(c a) USE_HASH(a)`가 선행 채용공고=Build(Id 3 위)·지원내역=Probe(Id 4 아래)·해시 조인·양쪽 Full Scan을 그대로 만들어 Id 2~4와 일치합니다 |
| ④ | ✗ | `USE_MERGE(a)`는 소트 머지 조인이라 두 입력 위에 `SORT JOIN`이 붙습니다. 플랜엔 SORT JOIN이 없고 SORT GROUP BY만 있어 조인 방식이 다릅니다 |

---

## ✅ 이 문제의 핵심

1. **실행계획→SQL 역추론은 세 좌표로 읽습니다.** 조인 방식(HASH JOIN), 빌드/프로브 순서(위 자식=Build=선행), 액세스 방식(양쪽 TABLE ACCESS FULL).
2. **해시 조인의 위쪽 자식이 Build Input이자 선행 테이블**입니다. 플랜은 채용공고(Id 3)가 Build, 지원내역(Id 4)이 Probe이므로 `LEADING(c a)`가 필요합니다.
3. **조인 방식을 바꾸면 노드가 바뀝니다.** `USE_NL`은 NESTED LOOPS+인덱스, `USE_MERGE`는 MERGE JOIN+SORT JOIN을 만들어 HASH JOIN 플랜과 어긋납니다.
4. **선행/후행을 뒤집으면 위·아래 자식이 뒤바뀝니다.** `LEADING(a c)`는 지원내역을 Build로 올려 플랜과 모순됩니다 — 방식·순서를 뒤바꾼 값스왑 오답입니다.

📌 한 줄 정리: 플랜이 HASH JOIN + 위 자식 채용공고(Build) + 아래 자식 지원내역(Probe) + 양쪽 Full Scan이므로, 이를 내는 SQL은 `LEADING(c a) USE_HASH(a)`인 ③뿐이고 나머지는 조인 방식·빌드 순서를 뒤바꾼 SQL이다.
