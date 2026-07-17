<!--meta
번호: 15
대상장: 6
대상절: 6.2
절제목: Direct Path Insert
문제유형: 적절하지_않은_것
보조자료: SQL
DBMS: 오라클
정답: 3
선택지유형: 서술형
함정유형: [정반대_진술]
대상개념: [Direct_Path_Insert, nologging, append]
자극물밀도: SQL
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 15

### 문제

대량 이관 배치에서 아래와 같이 `append` 힌트와 `nologging` 속성을 함께 사용해 데이터를 적재한다. 이 Direct Path Insert 방식의 효과로 가장 적절하지 <u>않은</u> 것은?

#### [아 래]

```sql
alter table sales_archive nologging;

insert /*+ append */ into sales_archive
select * from sales
where  sale_dt < date '2025-01-01';

commit;
```

### 선택지

① 데이터를 버퍼 캐시를 우회해 세그먼트 HWM(고수위) 위쪽에 직접 기록하므로, 버퍼 캐시 경합이 줄어든다.
② 대상 테이블이 nologging이고 append가 적용되면, 삽입되는 데이터에 대한 Redo 발생이 최소화된다.
③ append 힌트는 대상 테이블에 배타적(TM) Lock을 걸지 않으므로, 다른 세션이 동시에 같은 테이블에 INSERT를 수행할 수 있다.
④ HWM 아래에 비어 있는 블록(삭제로 생긴 여유 공간)을 재사용하지 않고 HWM 위에 기록하므로, 세그먼트가 커질 수 있다.

---

### 정답 — ③

### 왜 ③인가

Direct Path Insert(`/*+ append */`)의 특징을 하나씩 대응시키면 ③만 방향이 뒤집혀 있습니다.

- **①(참)**: append는 데이터를 버퍼 캐시에 담지 않고 **세그먼트 HWM 위쪽 새 블록에 직접(Direct Path)** 기록합니다. 버퍼 캐시를 거치지 않으니 캐시 경합·오버헤드가 줄어듭니다.
- **②(참)**: 대상 테이블이 `nologging`이고 direct path(append)가 적용되면, 삽입 데이터에 대한 **Redo가 최소화**됩니다(공간·딕셔너리 변경 정도만 로깅). 대량 적재 속도를 높이는 핵심 효과입니다.
- **④(참)**: direct path는 **HWM 아래의 여유 공간(삭제로 빈 블록)을 재사용하지 않고** HWM 위에만 붙여 씁니다. 그래서 반복하면 세그먼트가 실제 데이터량보다 커질 수 있습니다.

**③(거짓 — 정반대 진술)**: append(Direct Path Insert)는 오히려 대상 테이블에 **배타적 TM Lock(Exclusive)** 을 획득합니다. 그 결과 **커밋 전까지 다른 세션은 같은 테이블에 INSERT·UPDATE·DELETE를 수행할 수 없습니다.** ③은 "Lock을 걸지 않아 동시 INSERT가 가능하다"라며 사실을 정확히 뒤집었습니다. Direct Path의 대표적 제약(동시 DML 차단)을 반대로 진술했으므로 가장 부적절합니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ○ | append는 버퍼 캐시를 우회해 HWM 위 새 블록에 직접 기록하므로 버퍼 캐시 경합이 줄어듭니다 |
| ② | ○ | nologging 테이블에 direct path가 적용되면 삽입 데이터의 Redo가 최소화됩니다(공간·딕셔너리 변경만 로깅) |
| ③ | **✗** | 방향이 반대입니다. append는 대상 테이블에 배타적 TM Lock을 걸어, 커밋 전까지 다른 세션의 동시 DML(INSERT 포함)을 차단합니다 |
| ④ | ○ | HWM 아래 여유 공간을 재사용하지 않고 HWM 위에 붙여 쓰므로 세그먼트가 커질 수 있습니다 |

---

## ✅ 이 문제의 핵심

1. **Direct Path(append) = 버퍼 캐시 우회 + HWM 위 직접 기록.** 캐시 경합이 줄고 대량 적재가 빠릅니다.
2. **nologging + append → Redo 최소화.** 단, 복구를 위해서는 이후 백업 전략을 고려해야 합니다.
3. **여유 공간 미재사용.** HWM 아래 빈 블록을 건너뛰고 위에만 쓰므로 세그먼트가 부풀 수 있습니다.
4. **배타적 TM Lock으로 동시 DML 차단.** 커밋 전까지 같은 테이블에 다른 세션의 INSERT/UPDATE/DELETE가 막힙니다 — 이 제약을 반대로 읽지 않도록 주의합니다.

📌 한 줄 정리: Direct Path Insert는 버퍼 캐시를 우회해 HWM 위에 직접 기록하고 nologging과 함께 Redo를 최소화하지만, 대상 테이블에 배타적 TM Lock을 걸어 커밋 전까지 동시 DML을 차단합니다.
