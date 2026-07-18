<!--meta
번호: 15
대상장: 6
대상절: 6.2
절제목: DML 튜닝
문제유형: 적절하지_않은_것
보조자료: SQL
DBMS: 오라클
정답: 4
선택지유형: 서술형
함정유형: [정반대_진술]
대상개념: [Direct_Path_Insert, 병렬_DML, nologging]
자극물밀도: SQL
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 15

### 문제

수질 관측소가 하루치 원시 측정값 약 4,000만 건을 스테이징 테이블(수질측정_적재)에서 본 테이블(수질측정)로 적재하는 배치이다. 개발자는 아래처럼 세션에 병렬 DML을 활성화한 뒤 `APPEND PARALLEL` 힌트로 대량 INSERT를 수행하고, **커밋하기 전에** 같은 세션에서 방금 적재한 행 수를 확인하려 한다. 이 배치의 병렬 DML·Direct Path Insert 동작에 대한 설명으로 가장 적절하지 <u>않은</u> 것은?

#### [아 래]

```sql
ALTER SESSION ENABLE PARALLEL DML;

INSERT /*+ APPEND PARALLEL(t, 4) */ INTO 수질측정 t
SELECT * FROM 수질측정_적재;

-- 아직 COMMIT 하지 않은 상태에서
SELECT COUNT(*) FROM 수질측정;      -- 같은 트랜잭션에서 재조회 시도
```

### 선택지

① `ALTER SESSION ENABLE PARALLEL DML`을 먼저 실행해야 INSERT 문의 PARALLEL 힌트가 병렬 DML로 동작한다. 세션에서 활성화하지 않으면 INSERT 자체는 직렬로 처리될 수 있다.

② APPEND 힌트로 Direct Path Insert가 되어 기존 세그먼트의 프리리스트를 거치지 않고 HWM(고수위) 위 새 블록에 기록하며, 병렬 INSERT는 각 PX 서버가 자기 임시 세그먼트에 적재한 뒤 HWM을 올려 병합한다.

③ 대상 테이블이 NOLOGGING이고 Direct Path로 적재하면 데이터에 대한 redo 생성이 최소화되어 적재는 빨라지지만, 미디어 복구가 불가능해질 수 있어 적재 직후 백업이 필요할 수 있다.

④ 병렬 DML로 INSERT한 직후, 같은 트랜잭션 안에서 COMMIT 없이 곧바로 `SELECT COUNT(*) FROM 수질측정`으로 방금 넣은 행 수를 조회해 확인할 수 있다.

---

### 정답 — ④

### 왜 ④인가

병렬 DML(Parallel DML)로 세그먼트를 수정한 세션은 **그 트랜잭션 안에서 같은 객체를 다시 읽거나 고칠 수 없습니다.** 커밋(또는 롤백)으로 트랜잭션을 끝내야 비로소 재접근이 허용됩니다. 이 규칙을 어기고 커밋 전에 같은 객체를 조회하면 오라클은 `ORA-12838: cannot read/modify an object after modifying it in parallel` 오류를 던집니다.

```text
[ 병렬 DML 후 같은 트랜잭션에서의 재접근 ]
  INSERT /*+ APPEND PARALLEL */ ... 수질측정   → 병렬 DML로 세그먼트 수정
  (COMMIT 안 함)
  SELECT COUNT(*) FROM 수질측정                → ORA-12838 (재접근 불가)

  허용되는 순서 : ... INSERT ... → COMMIT → SELECT COUNT(*)  (그제야 조회 가능)
```

④은 이 제약을 정반대로 뒤집었습니다. "커밋 없이 같은 트랜잭션에서 곧바로 조회해 확인할 수 있다"고 했지만, 실제로는 커밋 전 재접근이 막혀 오류가 납니다. 방금 넣은 행 수를 확인하려면 먼저 COMMIT 한 뒤 조회해야 합니다. 그래서 부적절한 진술은 ④입니다.

①②③는 병렬 DML의 활성화 전제(①), Direct Path의 HWM 위 기록·PX 서버 병합(②), NOLOGGING+Direct Path의 redo 최소화와 복구 리스크(③)를 모두 옳게 서술합니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ○ | 병렬 DML은 세션에서 `ENABLE PARALLEL DML`로 활성화해야 INSERT가 병렬로 동작합니다. 활성화 없이는 힌트가 있어도 DML이 직렬로 처리될 수 있습니다 |
| ② | ○ | APPEND는 Direct Path로 HWM 위 새 블록에 기록하고, 병렬 INSERT는 각 PX 서버가 임시 세그먼트에 적재 후 HWM을 올려 병합합니다 |
| ③ | ○ | NOLOGGING+Direct Path는 데이터 redo를 최소화해 적재는 빠르나 미디어 복구가 불가능해질 수 있어, 적재 후 백업이 권장됩니다 |
| ④ | **✗** | 병렬 DML 후 커밋 전에는 같은 트랜잭션에서 그 객체를 재조회할 수 없습니다(ORA-12838). 확인하려면 먼저 COMMIT 해야 합니다 |

---

## ✅ 이 문제의 핵심

1. **병렬 DML은 세션 활성화(`ENABLE PARALLEL DML`)가 전제**입니다. 활성화 없이는 힌트가 있어도 DML이 직렬로 갈 수 있습니다.
2. **병렬 DML로 수정한 객체는 같은 트랜잭션에서 재접근 불가**입니다. 커밋/롤백 전에 조회·수정하면 ORA-12838이 납니다.
3. **APPEND(Direct Path)는 HWM 위 새 블록에 기록**하고, 병렬 INSERT는 PX 서버별 임시 세그먼트를 병합합니다.
4. **NOLOGGING+Direct Path는 redo를 최소화**해 빠르지만 미디어 복구 리스크가 있어 적재 후 백업이 필요할 수 있습니다.

📌 한 줄 정리: 병렬 DML로 적재한 객체는 같은 트랜잭션에서 커밋 전 재조회가 막혀 ORA-12838이 나므로, "커밋 없이 곧바로 조회해 확인할 수 있다"는 것은 규칙을 뒤집은 진술입니다.
