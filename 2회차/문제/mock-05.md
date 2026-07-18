<!--meta
번호: 5
대상장: 2
대상절: 2.1
절제목: 예상 실행계획 확인
문제유형: 적절한_것
보조자료: 없음
DBMS: 공통
정답: 3
선택지유형: 서술형
함정유형: [경계_오해]
대상개념: [예상_실행계획, AutoTrace, DBMS_XPLAN]
자극물밀도: 없음
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 5

### 문제

예상(추정) 실행계획을 확인하는 여러 도구의 **문장 수행 여부**에 대한 설명으로 가장 적절한 것은?

### 선택지

① 오라클의 `SET AUTOTRACE TRACEONLY`(EXPLAIN·STATISTICS를 함께 켠 상태)는 결과 행을 화면에 출력하지 않으므로, 대상 SELECT문 자체도 전혀 수행하지 않는다.
② SQL Server의 `SET SHOWPLAN_TEXT ON`은 대상 문장을 실제로 수행한 뒤 실측 통계가 담긴 실제 실행계획을 반환한다.
③ SQL Server의 `SET SHOWPLAN_ALL ON`은 이후 문장을 수행하지 않고 예상 실행계획만 반환하는 반면, `SET STATISTICS PROFILE ON`은 문장을 실제로 수행한 뒤 실측 행 수가 포함된 실제 실행계획을 반환한다.
④ 오라클의 `EXPLAIN PLAN FOR ...`는 문장을 수행하면서 실측 행 수까지 PLAN_TABLE에 적재하므로, `DBMS_XPLAN.DISPLAY`로 조회하면 실측치가 반영된 실제 실행계획을 볼 수 있다.

---

### 정답 — ③

### 왜 ③인가

예상 계획 도구를 고를 때의 핵심 갈림길은 **"문장을 실제로 돌리는가"** 하나입니다. 도구마다 이 경계가 다릅니다.

```text
문장 미수행 (예상 계획만)
  오라클     : EXPLAIN PLAN FOR <문장>  → PLAN_TABLE 적재(추정치)
               SET AUTOTRACE TRACEONLY EXPLAIN
  SQL Server : SET SHOWPLAN_TEXT / SHOWPLAN_ALL / SHOWPLAN_XML ON

문장 수행함 (실제 계획, 실측 행 수 포함)
  오라클     : SET AUTOTRACE TRACEONLY STATISTICS (STATISTICS를 켜면 수행)
  SQL Server : SET STATISTICS PROFILE / STATISTICS XML ON
```

③는 SQL Server 두 도구의 경계를 정확히 갈랐습니다. `SHOWPLAN_ALL ON`은 문장을 **수행하지 않고** 추정 계획만 내고, `STATISTICS PROFILE ON`은 문장을 **실제로 수행해** 실측 행 수가 담긴 실제 계획을 냅니다. "예상은 미수행, 실제는 수행"이라는 원칙 그대로입니다.

나머지는 이 경계를 뭉갰습니다.

- ①은 `TRACEONLY`에 **STATISTICS까지 켜면** 통계를 모으기 위해 SELECT문을 **실제로 수행**한다는 사실을 놓쳤습니다. 문장을 돌리지 않는 것은 `TRACEONLY EXPLAIN`(계획만)일 때뿐입니다. 결과 행을 화면에 안 찍는 것과 문장을 안 돌리는 것은 별개입니다.
- ②는 `SHOWPLAN`을 실행 도구로 오해했습니다. `SHOWPLAN_*`은 미수행 예상 계획 도구입니다.
- ④은 `EXPLAIN PLAN`이 문장을 수행해 실측치를 담는다고 했지만, `EXPLAIN PLAN`은 문장을 돌리지 않고 **추정** 계획만 PLAN_TABLE에 적재합니다. 실측 행 수를 보려면 `gather_plan_statistics` 힌트로 실제 수행한 뒤 `DBMS_XPLAN.DISPLAY_CURSOR`를 써야 합니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ✗ | `TRACEONLY`에 STATISTICS가 켜져 있으면 통계 수집을 위해 SELECT문을 실제로 수행합니다. 결과 행 미출력과 문장 미수행은 다릅니다. 미수행은 `TRACEONLY EXPLAIN`일 때뿐입니다 |
| ② | ✗ | `SHOWPLAN_TEXT ON`은 문장을 수행하지 않고 예상 계획만 반환합니다. 실제 수행 도구로 서술한 것은 경계를 뒤집은 것입니다 |
| ③ | **○** | `SHOWPLAN_ALL ON`은 미수행 예상 계획, `STATISTICS PROFILE ON`은 수행 후 실제 계획을 냅니다. 두 도구의 경계가 정확합니다 |
| ④ | ✗ | `EXPLAIN PLAN`은 문장을 수행하지 않고 추정 계획만 적재합니다. 실측 행 수는 담기지 않으며, 그것을 보려면 `DISPLAY_CURSOR`가 필요합니다 |

---

## ✅ 이 문제의 핵심

1. **결과 행 미출력 ≠ 문장 미수행.** `AUTOTRACE TRACEONLY`라도 STATISTICS가 켜지면 통계를 모으려고 문장을 실제로 돌립니다.
2. 오라클에서 진짜 미수행 예상 계획은 `EXPLAIN PLAN`(추정치만 PLAN_TABLE 적재)과 `AUTOTRACE TRACEONLY EXPLAIN`입니다.
3. SQL Server에서 `SHOWPLAN_*`은 미수행 예상 계획, `STATISTICS PROFILE/XML`은 수행 후 실제 계획입니다.
4. 실측 행 수가 필요하면 문장을 실제로 돌린 뒤(오라클은 `gather_plan_statistics` + `DISPLAY_CURSOR`) 얻어야 합니다. `EXPLAIN PLAN`으로는 얻을 수 없습니다.

📌 한 줄 정리: `SHOWPLAN_*`은 문장을 돌리지 않는 예상 계획, `STATISTICS PROFILE`은 돌리는 실제 계획이며, `AUTOTRACE TRACEONLY`도 STATISTICS가 켜지면 문장을 실제로 수행한다는 경계가 관건입니다.
