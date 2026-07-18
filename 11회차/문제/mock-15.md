<!--meta
번호: 15
대상장: 6
대상절: 6.2
절제목: DML 튜닝
문제유형: 적절하지_않은_것
보조자료: SQL
DBMS: 오라클
정답: 3
선택지유형: 혼합
함정유형: [정반대_진술]
대상개념: [Direct_Path_Insert, 병렬_DML, nologging]
자극물밀도: SQL
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 15

### 문제

지적측량 성과 관리의 야간 배치가 당일 접수·처리된 측량성과(약 9,000만 행)를 스테이징에서 `측량성과이력`(약 15억 행)으로 대량 적재한다. 적재 시간을 줄이려고 아래처럼 `APPEND` 힌트와 병렬 DML을 적용했다. `측량성과이력` 세그먼트는 NOLOGGING이고 DB는 force logging이 아니다. 이 대량 적재 튜닝에 대한 설명으로 가장 적절하지 <u>않은</u> 것은?

#### [아 래]

```sql
-- 당일 측량성과를 측량성과이력에 대량 적재하는 야간 배치
ALTER SESSION ENABLE PARALLEL DML;

INSERT /*+ APPEND PARALLEL(t, 4) */ INTO 측량성과이력 t
SELECT * FROM 성과_스테이징;

-- COMMIT 전, 같은 세션에서 적재 결과를 곧바로 SELECT 하려 시도한다
```

### 선택지

① `INSERT /*+ APPEND */`는 Direct Path Insert로 동작해, HWM 위쪽에 새 블록을 할당하며 데이터를 기록하고 버퍼 캐시와 freelist 탐색을 우회하므로 대량 적재가 빨라진다.

② `ALTER SESSION ENABLE PARALLEL DML` 후 병렬 INSERT를 수행하면 여러 PX 서버가 각자 자기 익스텐트에 direct path로 적재하며, 이때 대상 테이블은 배타 모드로 잠겨 커밋 전까지 같은 테이블에 대한 다른 세션의 DML은 대기한다.

③ 세그먼트가 NOLOGGING이면 direct path뿐 아니라 일반(conventional) 인서트에도 redo 절감이 적용되므로, 병렬 없이 일반 INSERT만 발행해도 데이터에 대한 redo가 사라져 대량 적재 부하가 크게 준다.

④ direct path로 적재한 세그먼트는 커밋 전에는 같은 트랜잭션이라도 다시 읽거나 수정할 수 없어, 위 배치가 커밋 전에 `측량성과이력`을 SELECT하면 ORA-12838이 발생한다 — 조회하려면 먼저 커밋해야 한다.

---

### 정답 — ③

### 왜 ③인가

NOLOGGING의 redo 절감은 **Direct Path 적재에만** 걸립니다. 세그먼트를 NOLOGGING으로 두어도, 버퍼 캐시를 거치는 일반(conventional) 인서트는 변경분을 정상적으로 redo에 기록합니다 — redo가 줄어드는 것은 `APPEND`(direct path)로 HWM 위 새 블록에 직접 쓰고, 그 세그먼트가 NOLOGGING이며, DB가 force logging이 아닐 때뿐입니다.

```text
[ redo 절감 성립 조건 ]
일반 인서트 + NOLOGGING        : 버퍼 캐시 경유 → 데이터 redo 정상 기록 (절감 없음)
Direct Path(APPEND) + NOLOGGING + non-force-logging : 데이터 redo 최소화 (절감 성립)
※ NOLOGGING은 "direct path일 때만" 데이터 로깅을 건너뛴다
```

③은 "NOLOGGING이면 일반 인서트에도 redo 절감이 적용되어 병렬 없이 일반 INSERT만으로도 redo가 사라진다"고 했는데, 이는 실제 동작을 **정반대**로 뒤집은 것입니다. NOLOGGING은 conventional 경로에는 효과가 없으며, direct path가 아니면 세그먼트 속성과 무관하게 redo가 그대로 쌓입니다. 그래서 부적절한 진술은 ③입니다.

①②④는 각각 direct path의 HWM 위 적재·버퍼 캐시 우회(①), 병렬 DML의 PX별 적재와 테이블 배타 잠금(②), direct path 적재 세그먼트를 커밋 전 재접근 시 ORA-12838(④)을 옳게 서술합니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ○ | APPEND는 direct path로 HWM 위 새 블록에 기록하고 버퍼 캐시·freelist를 우회하므로 대량 적재가 빨라집니다 |
| ② | ○ | 병렬 DML을 켜면 PX 서버가 각자 익스텐트에 direct path로 적재하고, 대상 테이블은 배타 모드로 잠겨 커밋 전까지 다른 세션의 DML이 대기합니다 |
| ③ | **✗** | NOLOGGING의 redo 절감은 direct path 경로에만 적용됩니다. 일반 인서트는 버퍼 캐시를 거쳐 데이터 redo를 정상 기록하므로 "일반 INSERT만으로 redo가 사라진다"는 정반대입니다 |
| ④ | ○ | direct path 적재 세그먼트는 커밋 전 같은 트랜잭션에서도 재접근이 막혀, 커밋 전 SELECT 시 ORA-12838이 나며 조회하려면 먼저 커밋해야 합니다 |

---

## ✅ 이 문제의 핵심

1. **NOLOGGING의 redo 절감은 direct path 전용**입니다. 일반 인서트는 세그먼트가 NOLOGGING이어도 버퍼 캐시를 거쳐 데이터 redo를 정상 기록합니다.
2. **redo 절감 성립 3조건**은 direct path 적재 + 세그먼트 NOLOGGING + DB non-force-logging입니다. 하나라도 빠지면 데이터 redo가 쌓입니다.
3. **병렬 DML은 테이블을 배타 잠금**합니다. PX 서버가 각자 익스텐트에 적재하고 커밋 전까지 같은 테이블의 다른 DML이 대기합니다.
4. **direct path 적재분은 커밋 전 재접근 불가**입니다. 같은 트랜잭션이라도 커밋 전 SELECT·수정은 ORA-12838로 막힙니다.

📌 한 줄 정리: NOLOGGING은 direct path 경로에서만 데이터 redo를 줄이고 일반 인서트에는 효과가 없는데, ③은 "일반 INSERT에도 redo 절감이 적용되어 redo가 사라진다"고 정반대로 서술해 부적절합니다.
