<!--meta
번호: 10
대상장: 4
대상절: 4.1
절제목: NL 조인
문제유형: 적절하지_않은_것
보조자료: 실행계획
DBMS: 오라클
정답: 2
선택지유형: 코드형
함정유형: [값스왑]
대상개념: [NL_조인, 조인_방식_선택, 조인_순서]
자극물밀도: 실행계획_pipe_역공학
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 10

### 문제

수산물 위판 정산 조회 프로그램이 `위판장`(약 220건)·`위판낙찰`(약 190만 건)·`낙찰명세`(약 1억 2천만 건) 세 테이블을 조인해 특정 위판장의 낙찰 명세를 뽑는다. `위판낙찰`는 위판장코드로 `위판장`과, 낙찰명세는 낙찰번호로 `위판낙찰`와 이어진다(`위판장`과 `낙찰명세`를 직접 잇는 조인 칼럼은 없다). 네 후보 SQL은 SELECT 목록·WHERE 조건이 모두 같고 조인 힌트만 서로 다르다. 아래 실행계획을 **낸** SQL/힌트로 가장 적절하지 <u>않은</u> 것은?

#### [아 래]

```text
| Id  | Operation                       | Name        |
|-----|---------------------------------|-------------|
|   0 | SELECT STATEMENT                |             |
|   1 |  NESTED LOOPS                   |             |
|   2 |   NESTED LOOPS                  |             |
|*  3 |    TABLE ACCESS FULL            | 위판장       |
|   4 |    TABLE ACCESS BY INDEX ROWID  | 위판낙찰     |
|*  5 |     INDEX RANGE SCAN            | 위판낙찰_IX  |
|   6 |   TABLE ACCESS BY INDEX ROWID   | 낙찰명세     |
|*  7 |    INDEX RANGE SCAN             | 낙찰명세_IX  |
```

### 선택지

① 아래 SQL
```sql
SELECT /*+ LEADING(g e d) USE_NL(e) USE_NL(d) */
       g.위판장명, e.낙찰일자, d.어종코드, d.낙찰단가
  FROM 위판장 g, 위판낙찰 e, 낙찰명세 d
 WHERE e.위판장코드 = g.위판장코드
   AND d.낙찰번호 = e.낙찰번호
   AND g.위판구분 = '수산';
```

② 아래 SQL
```sql
SELECT /*+ LEADING(e g d) USE_NL(g) USE_NL(d) */
       g.위판장명, e.낙찰일자, d.어종코드, d.낙찰단가
  FROM 위판장 g, 위판낙찰 e, 낙찰명세 d
 WHERE e.위판장코드 = g.위판장코드
   AND d.낙찰번호 = e.낙찰번호
   AND g.위판구분 = '수산';
```

③ 아래 SQL
```sql
SELECT /*+ ORDERED USE_NL(e) USE_NL(d) */
       g.위판장명, e.낙찰일자, d.어종코드, d.낙찰단가
  FROM 위판장 g, 위판낙찰 e, 낙찰명세 d
 WHERE e.위판장코드 = g.위판장코드
   AND d.낙찰번호 = e.낙찰번호
   AND g.위판구분 = '수산';
```

④ 아래 SQL
```sql
SELECT /*+ LEADING(g e d) USE_NL(e d) */
       g.위판장명, e.낙찰일자, d.어종코드, d.낙찰단가
  FROM 위판장 g, 위판낙찰 e, 낙찰명세 d
 WHERE e.위판장코드 = g.위판장코드
   AND d.낙찰번호 = e.낙찰번호
   AND g.위판구분 = '수산';
```

---

### 정답 — ②

### 왜 ②인가

3-way 플랜은 **가장 깊이 왼쪽에 있는 테이블이 선행(드라이빙)** 이고, 위에서 아래로 NESTED LOOPS가 겹칠수록 조인 순서가 이어집니다. 두 좌표 — **조인 순서, 조인 방식** — 로 읽습니다.

```text
Id 3  TABLE ACCESS FULL 위판장    ← 안쪽 NL(Id 2)의 첫 자식 = 선행(드라이빙)
Id 4  ...BY INDEX ROWID 위판낙찰   ← 안쪽 NL의 후행 = 두 번째
Id 6  ...BY INDEX ROWID 낙찰명세   ← 바깥 NL(Id 1)의 후행 = 세 번째
```

- 조인 순서: **위판장 → 위판낙찰 → 낙찰명세**. 안쪽 NESTED LOOPS(Id 2)가 `위판장 ⋈ 위판낙찰`를, 바깥 NESTED LOOPS(Id 1)가 그 결과에 `낙찰명세`를 잇습니다. 선행은 가장 깊은 왼쪽인 위판장(Id 3)입니다.
- 조인 방식: NESTED LOOPS 두 개뿐이고 HASH JOIN·MERGE JOIN 노드가 없으므로 **두 조인 모두 NL**이며, 후행 위판낙찰·낙찰명세는 인덱스(Id 5·Id 7)로 탐색됩니다.

이 순서(`LEADING(g e d)`)와 방식(둘 다 NL)을 만드는 힌트는 **세 가지 표기가 모두 같은 플랜**을 냅니다.

```text
① LEADING(g e d) USE_NL(e) USE_NL(d)  : 선행 위판장, 둘 다 NL                → Id 1~7과 일치      ✔
③ ORDERED USE_NL(e) USE_NL(d)         : ORDERED=FROM 순서(g,e,d)를 조인 순서로 → LEADING(g e d)와 동일  ✔
④ LEADING(g e d) USE_NL(e d)          : USE_NL(e d)=위판낙찰·낙찰명세 모두 NL  → ①과 동일           ✔
② LEADING(e g d) USE_NL(g) USE_NL(d)  : 선행을 위판낙찰로 지정               → 플랜은 위판장이 선행   ✗
```

`ORDERED`는 FROM 절 순서(위판장 g, 위판낙찰 e, 낙찰명세 d)를 그대로 조인 순서로 삼으므로 `LEADING(g e d)`와 같고, `USE_NL(e d)`는 `USE_NL(e) USE_NL(d)`와 같은 지정입니다. 그래서 ①·③·④는 **선행=위판장 + 두 조인 NL**이라는 동일한 플랜을 냅니다.

②만 `LEADING(e g d)`로 **위판낙찰를 선행**으로 올립니다. 위판낙찰는 위판장코드로 위판장과, 낙찰번호로 낙찰명세와 모두 이어지므로 이 순서 자체는 유효한 조인 순서이지만, 그 플랜은 가장 깊은 왼쪽에 위판낙찰가 오게 되어 **위판장(Id 3)이 선행인 위 플랜과 어긋납니다**. 선행 테이블을 뒤바꾼 ②가 이 플랜을 내지 못하는 SQL입니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ○ | `LEADING(g e d)`로 선행=위판장(Id 3)·순서 위판장→위판낙찰→낙찰명세, `USE_NL` 둘로 두 조인 모두 NL — Id 1~7의 겹친 NESTED LOOPS 구조를 그대로 냅니다 |
| ② | **✗** | `LEADING(e g d)`가 위판낙찰를 선행으로 지정해 가장 깊은 왼쪽이 위판낙찰가 됩니다. 플랜의 최심 왼쪽(Id 3)은 위판장이므로 선행을 뒤바꾼 SQL이고, 이 플랜을 내지 못합니다 |
| ③ | ○ | `ORDERED`는 FROM 순서(위판장 g, 위판낙찰 e, 낙찰명세 d)를 조인 순서로 삼아 `LEADING(g e d)`와 동일하고, `USE_NL` 둘로 두 조인이 NL이라 ①과 같은 플랜을 냅니다 |
| ④ | ○ | `USE_NL(e d)`는 위판낙찰·낙찰명세를 함께 NL로 지정한 것이라 `USE_NL(e) USE_NL(d)`와 같고, `LEADING(g e d)`까지 동일해 ①과 같은 플랜을 냅니다 |

---

## ✅ 이 문제의 핵심

1. **3-way 플랜은 가장 깊은 왼쪽 테이블이 선행**입니다. 겹친 NESTED LOOPS에서 안쪽 NL(Id 2)이 위판장 ⋈ 위판낙찰를, 바깥 NL(Id 1)이 낙찰명세를 잇습니다 — 순서는 위판장→위판낙찰→낙찰명세.
2. **NESTED LOOPS만 있고 HASH/MERGE 노드가 없으면 두 조인 모두 NL**이며, 후행은 인덱스(Id 5·Id 7)로 탐색됩니다.
3. **같은 조인 순서·방식을 여러 힌트 표기가 낸다.** `ORDERED`(FROM 순서)·`USE_NL(e d)`(다중 지정)는 각각 `LEADING(g e d)`·`USE_NL(e) USE_NL(d)`와 같아 ①·③·④가 동일 플랜을 냅니다.
4. **선행을 바꾸면 플랜이 바뀝니다.** ②의 `LEADING(e g d)`는 위판낙찰를 선행으로 올려 최심 왼쪽이 달라지므로 이 플랜을 못 냅니다 — 선행 테이블을 뒤바꾼 값스왑입니다.

📌 한 줄 정리: 플랜이 선행=위판장(Id 3)·두 조인 모두 NL이므로 `LEADING(g e d)`+NL을 뜻하는 ①·③·④는 같은 플랜을 내지만, 위판낙찰를 선행으로 뒤바꾼 `LEADING(e g d)`의 ②만 이 플랜을 내지 못한다.
