<!--meta
번호: 5
대상장: 2
대상절: 2.1
절제목: 예상 실행계획 확인
문제유형: 적절한_것
보조자료: 없음
DBMS: 공통
정답: 2
선택지유형: 서술형
함정유형: [경계_오해]
대상개념: [예상_실행계획, DBMS_XPLAN, AutoTrace]
자극물밀도: 없음
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 5

### 문제

예상(추정) 실행계획을 조회하는 `DBMS_XPLAN.DISPLAY`와 실제 수행된 커서의 계획을 조회하는 `DBMS_XPLAN.DISPLAY_CURSOR`, 그리고 바인드 변수 때문에 둘이 갈릴 수 있는 상황에 대한 설명으로 가장 적절한 것은?

### 선택지

① `DBMS_XPLAN.DISPLAY_CURSOR`는 아직 수행하지 않은 문장의 예상 계획을 PLAN_TABLE에서 읽어 오는 함수이므로, `EXPLAIN PLAN`을 선행하지 않고도 `DISPLAY`와 서로 바꿔 써서 예상 계획을 확인할 수 있다.

② `DBMS_XPLAN.DISPLAY`는 `EXPLAIN PLAN`이 PLAN_TABLE에 적재한 예상 계획을 보여 주고, `DBMS_XPLAN.DISPLAY_CURSOR`는 라이브러리 캐시에 올라온 실제 수행된 커서의 계획을 보여 준다. 바인드 변수가 있으면 `EXPLAIN PLAN`은 그 값을 엿보지(bind peeking) 못해, 실제 수행 시의 계획과 서로 달라질 수 있다.

③ `EXPLAIN PLAN`은 대상 문장을 실제로 파싱·수행하면서 바인드 변수 값을 반영해 계획을 세우므로, `DISPLAY`로 조회한 예상 계획이 곧 실제 커서의 계획과 같다.

④ AUTOTRACE의 `SET AUTOTRACE TRACEONLY EXPLAIN`으로 출력되는 계획은 라이브러리 캐시의 실제 커서에서 가져온 것이라, 실측 행 수가 포함된 실제 실행계획이며 `DISPLAY_CURSOR`로 본 계획과 같다.

---

### 정답 — ②

### 왜 ②인가

두 함수는 **어디에서 계획을 읽어 오는가**가 다릅니다. 이 출처 경계가 문제의 핵심입니다.

```text
DBMS_XPLAN.DISPLAY
   출처 : PLAN_TABLE (EXPLAIN PLAN이 적재한 예상 계획)
   성격 : 문장 미수행, 추정치 기반 예상 계획
   바인드 : 값을 엿보지 못함 → 기본 가정으로 계획 산출

DBMS_XPLAN.DISPLAY_CURSOR
   출처 : 라이브러리 캐시 / V$SQL_PLAN (실제 수행된 커서)
   성격 : 실제 수행한 문장의 실제 실행계획
   바인드 : 첫 수행 시 실제 값을 엿봄(bind peeking) → 그 값에 맞춘 계획
```

②은 이 경계를 정확히 갈랐습니다. `DISPLAY`는 `EXPLAIN PLAN`이 남긴 **예상** 계획을, `DISPLAY_CURSOR`는 **실제 수행된 커서**의 계획을 조회합니다. 그리고 바인드 변수가 있으면 `EXPLAIN PLAN`은 그 값을 엿보지 못한 채 기본 가정으로 계획을 세우므로, 실제 수행 시 bind peeking을 거친 계획과 **달라질 수 있습니다**. 예상 계획을 신뢰하다 실제와 어긋나는 전형적 지점입니다.

나머지는 두 함수의 출처·성격을 뒤섞었습니다.

- ①는 `DISPLAY_CURSOR`를 "PLAN_TABLE의 예상 계획을 읽는 함수"로 봤지만, 이 함수는 **라이브러리 캐시의 실제 수행 커서**를 읽습니다. `DISPLAY`와 서로 바꿔 쓸 수 있는 것이 아닙니다.
- ③은 `EXPLAIN PLAN`이 문장을 수행하고 바인드 값을 반영한다고 했으나, `EXPLAIN PLAN`은 문장을 **수행하지 않고** 바인드 값도 **엿보지 않습니다.** 그래서 예상과 실제가 갈릴 수 있습니다.
- ④는 `TRACEONLY EXPLAIN`을 실제 커서 조회로 오해했습니다. 이 옵션은 `EXPLAIN PLAN` 방식의 **예상** 계획을 낼 뿐, 문장을 수행하지 않아 실측 행 수가 담기지 않습니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ✗ | `DISPLAY_CURSOR`는 PLAN_TABLE이 아니라 라이브러리 캐시의 실제 수행 커서를 읽습니다. `DISPLAY`와 바꿔 쓸 수 있는 예상 계획 함수가 아닙니다 |
| ② | **○** | `DISPLAY`는 PLAN_TABLE의 예상 계획, `DISPLAY_CURSOR`는 실제 수행된 커서의 계획을 조회하며, `EXPLAIN PLAN`은 bind peeking을 못 해 실제와 갈릴 수 있습니다. 출처와 원인이 정확합니다 |
| ③ | ✗ | `EXPLAIN PLAN`은 문장을 수행하지도, 바인드 값을 엿보지도 않습니다. 예상 계획과 실제 커서 계획이 갈릴 수 있는 이유가 바로 이것입니다 |
| ④ | ✗ | `TRACEONLY EXPLAIN`은 `EXPLAIN PLAN` 방식의 예상 계획을 낼 뿐 문장을 수행하지 않아 실측 행 수가 없고, 실제 커서에서 가져온 것도 아닙니다 |

---

## ✅ 이 문제의 핵심

1. **`DISPLAY` = PLAN_TABLE의 예상 계획**, **`DISPLAY_CURSOR` = 라이브러리 캐시의 실제 커서 계획.** 출처가 다릅니다.
2. `EXPLAIN PLAN`은 문장을 **수행하지 않고** 바인드 값을 **엿보지 않습니다** — 그래서 예상 계획이 나옵니다.
3. 실제 수행은 첫 파싱 때 바인드 값을 엿보므로(bind peeking), 예상 계획과 **다른 계획**이 나올 수 있습니다.
4. `TRACEONLY EXPLAIN`은 예상 계획 도구입니다. 실측 행 수가 담긴 실제 계획을 보려면 실제 수행 후 `DISPLAY_CURSOR`를 써야 합니다.

📌 한 줄 정리: `DISPLAY`는 PLAN_TABLE의 예상 계획을, `DISPLAY_CURSOR`는 실제 수행된 커서의 계획을 조회하며, `EXPLAIN PLAN`은 바인드 값을 엿보지 못해 예상과 실제가 갈릴 수 있습니다.
