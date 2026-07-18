<!--meta
번호: 3
대상장: 2
대상절: 2.1
절제목: 예상 실행계획 확인
문제유형: 적절한_것
보조자료: 없음
DBMS: 공통
정답: 2
선택지유형: 코드형
함정유형: [오라클↔SQLServer_뒤바꿈]
대상개념: [예상_실행계획, AutoTrace]
자극물밀도: 없음
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 3

### 문제

쿼리를 실제로 수행하지 않고 옵티마이저가 세운 **예상(추정) 실행계획**만 확인하려 한다. 각 DBMS의 도구 사용에 대한 설명으로 가장 적절한 것은?

### 선택지

① 오라클 — `SET SHOWPLAN_TEXT ON` 을 실행한 뒤 SELECT문을 던지면, 문장을 수행하지 않고 예상 실행계획만 텍스트로 반환한다.
② 오라클 — SQL*Plus에서 `SET AUTOTRACE TRACEONLY EXPLAIN` 설정 후 SELECT문을 실행하면, 문장을 수행하지 않고 예상 실행계획만 출력된다.
③ SQL Server — `EXPLAIN PLAN FOR SELECT ...;` 로 계획을 적재한 뒤 `SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY);` 로 조회하면 예상 실행계획이 표시된다.
④ SQL Server — `SET STATISTICS PROFILE ON` 을 실행한 뒤 쿼리를 던지면, 쿼리를 수행하지 않고 예상 실행계획만 반환한다.

---

### 정답 — ②

### 왜 ②인가

먼저 두 DBMS의 도구를 **소속별로** 정리합니다. 이 문제의 오답은 전부 도구를 반대편 DBMS로 옮겨 붙인 것입니다.

```text
오라클(예상 계획, 미수행)
  · EXPLAIN PLAN FOR <문장>;  → PLAN_TABLE에 적재(화면 출력 없음)
       확인:  SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY);
  · SET AUTOTRACE TRACEONLY EXPLAIN  → SELECT문을 수행하지 않고 계획만

SQL Server(예상 계획, 미수행)
  · SET SHOWPLAN_TEXT ON  /  SET SHOWPLAN_ALL ON  /  SET SHOWPLAN_XML ON
       → 이후 문장을 수행하지 않고 예상 계획만 반환
SQL Server(실제 계획, 수행함)
  · SET STATISTICS PROFILE ON  /  SET STATISTICS XML ON
       → 쿼리를 실제 수행하고 실측 행 수까지 담긴 실제 계획 반환
```

②은 오라클 SQL*Plus의 정통 용법입니다. `SET AUTOTRACE ON` 은 문장을 **수행하고** 계획과 통계를 함께 보여 주지만, `TRACEONLY EXPLAIN` 을 주면 SELECT문을 **실제로 수행하지 않고** 예상 실행계획만 출력합니다. "예상 계획만, 미수행"이라는 요구에 정확히 부합합니다.

나머지는 도구의 **소속 DBMS가 뒤바뀌었거나**(①③), **수행 여부가 반대**(④)입니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ✗ | `SET SHOWPLAN_TEXT ON` 은 SQL Server 구문입니다. 오라클에는 이 명령이 없어, 오라클에 붙이면 뒤바뀐 서술이 됩니다 |
| ② | **○** | 오라클 SQL*Plus의 `SET AUTOTRACE TRACEONLY EXPLAIN` 은 SELECT문을 수행하지 않고 예상 실행계획만 출력합니다 |
| ③ | ✗ | `EXPLAIN PLAN` 과 `DBMS_XPLAN.DISPLAY` 는 오라클 도구입니다. 함수 자체는 존재하나 용도가 오라클용이라, SQL Server 절차로 제시한 것은 DBMS를 뒤바꾼 서술입니다 |
| ④ | ✗ | `SET STATISTICS PROFILE ON` 은 쿼리를 실제 수행해 실측치가 담긴 실제 계획을 냅니다. "수행하지 않고 예상 계획만"과 반대입니다 |

---

## ✅ 이 문제의 핵심

1. **예상 계획 = 미수행, 실제 계획 = 수행.** 요구가 "예상"이면 문장을 돌리지 않는 도구를 골라야 합니다.
2. 오라클: `EXPLAIN PLAN` + `DBMS_XPLAN.DISPLAY`, 또는 `SET AUTOTRACE TRACEONLY EXPLAIN`.
3. SQL Server: 예상은 `SET SHOWPLAN_TEXT/ALL/XML ON`, 실제는 `SET STATISTICS PROFILE/XML ON`.
4. 오답은 도구가 **틀린 게 아니라 소속 DBMS가 뒤바뀐** 경우가 많습니다. 명령이 어느 진영 것인지부터 확인하세요.

📌 한 줄 정리: 예상 실행계획을 미수행으로 얻는 정통 방법은 오라클의 `SET AUTOTRACE TRACEONLY EXPLAIN`(그리고 `EXPLAIN PLAN`)이며, `SHOWPLAN`·`STATISTICS`는 SQL Server 쪽 도구입니다.
