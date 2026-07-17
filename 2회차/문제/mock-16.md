<!--meta
번호: 16
대상장: 6
대상절: 6.3
절제목: 데이터베이스 Call 최소화
문제유형: 적절한_것
보조자료: SQL
DBMS: 오라클
정답: 3
선택지유형: 서술형
함정유형: [값스왑]
대상개념: [Array_Processing, 스칼라_서브쿼리_캐싱, User_Call]
자극물밀도: SQL
계산요구: 있음
출처: 생성
상태: 검수완료
-->

## 문제 16

### 문제

배치 프로그램이 이벤트 로그 150만 건을 아래 SQL로 전량 Fetch해 파일로 출력한다. 스칼라 서브쿼리로 장비명을 함께 조회하며, dev_id의 서로 다른 값(distinct)은 40종뿐이다. 수행 통계가 함께 주어졌을 때 데이터베이스 Call 최소화에 대한 해석·처방으로 가장 적절한 것은?

#### [아 래]

```sql
SELECT e.evt_id,
       e.evt_dtm,
       e.dev_id,
       (SELECT d.dev_nm FROM device d WHERE d.dev_id = e.dev_id) AS dev_nm
FROM   event_log e
WHERE  e.evt_dtm >= DATE '2026-06-01';
```

```text
[ 수행 통계 ]
항목                          값
--------------------------------------------
반환 행 수(rows)              1,500,000
Fetch Call 횟수               3,001
device 최대 조회 대상         distinct dev_id = 40 종
```

### 선택지

① Fetch Call이 3,001회이므로 ArraySize는 약 50이며, ArraySize를 키우면 device 조회 횟수가 줄어 스칼라 서브쿼리 캐싱 효과가 커진다.

② 스칼라 서브쿼리 캐싱이 Fetch Call 횟수를 3,001회에서 줄여 네트워크 왕복을 감소시키고, ArraySize를 조정하면 device 조회가 40회 수준으로 줄어든다.

③ ArraySize는 1,500,000 ÷ (3,001 − 1) = 500이며, ArraySize를 더 키우면 Fetch Call(User Call) 횟수가 줄어 왕복이 감소한다. 한편 스칼라 서브쿼리 캐싱은 dev_id가 40종뿐이라 device 조회를 최대 40회 수준으로 줄인다.

④ ArraySize와 무관하게 Fetch Call은 반환 행 수와 항상 같으므로, 왕복을 줄이려면 스칼라 서브쿼리 캐싱만이 유효하다.

---

### 정답 — ③

### 왜 ③인가

두 최적화는 **줄이는 대상이 서로 다릅니다.** 하나는 클라이언트–서버 왕복(Fetch Call = User Call), 다른 하나는 서브쿼리 블록의 반복 실행입니다.

```text
[ArraySize 산출]
  ArraySize = 반환 행 수 ÷ (Fetch Call − 1)      ← 마지막 no-more-data fetch의 −1
            = 1,500,000 ÷ (3,001 − 1)
            = 1,500,000 ÷ 3,000
            = 500

[두 최적화의 효과 구분]
  Array Processing  → Fetch Call(User Call) 횟수를 줄임 = 네트워크 왕복 감소
       ArraySize 500 → 예: 1,000으로 키우면 Fetch ≈ 1,501회로 감소
  스칼라 서브쿼리 캐싱 → 같은 dev_id 재조회를 캐시로 대체
       device 조회를 최대 150만 → 40종(distinct) 수준으로 감소
```

- **ArraySize = 500**입니다. 한 번의 Fetch Call로 500행씩 실어 나르므로 150만 행에 3,000번의 Fetch(+마지막 빈 Fetch 1) = 3,001회입니다. ArraySize를 더 키우면 Fetch Call이 줄어 **User Call(왕복)** 이 감소합니다 — 이것이 Array Processing의 효과입니다.
- **스칼라 서브쿼리 캐싱**은 왕복이 아니라, `(SELECT dev_nm …)` 블록의 **반복 실행**을 줄입니다. dev_id가 40종뿐이므로 캐시가 히트해 device 조회가 최대 40회 수준으로 압축됩니다.

③은 ArraySize를 500으로 정확히 산출하고, 두 최적화의 효과(왕복 감소 vs 반복 조회 감소)를 올바르게 대응시켰습니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ✗ | ArraySize는 50이 아니라 1,500,000 ÷ 3,000 = 500입니다. 또 ArraySize를 키우는 것은 Fetch 왕복을 줄일 뿐, device 조회를 줄이는 것은 스칼라 캐싱의 몫입니다 |
| ② | ✗ | 두 효과를 통째로 뒤바꿨습니다. Fetch Call을 줄이는 것은 Array Processing이고, device 조회를 40회로 줄이는 것은 스칼라 서브쿼리 캐싱입니다 |
| ③ | **○** | ArraySize = 1,500,000 ÷ (3,001−1) = 500이 맞고, ArraySize↑는 Fetch(User Call) 왕복을, 스칼라 캐싱은 device 조회를 40종 수준으로 줄인다는 효과 구분이 정확합니다 |
| ④ | ✗ | Fetch Call은 반환 행 수와 같지 않습니다. ArraySize 500 덕에 150만 행이 3,001회로 묶였습니다. ArraySize를 키우면 왕복은 더 줄어듭니다 |

---

## ✅ 이 문제의 핵심

1. **ArraySize = 반환 행 수 ÷ (Fetch Call − 1)**. 여기서는 1,500,000 ÷ 3,000 = 500입니다.
2. **Array Processing은 Fetch Call(User Call) 왕복을 줄입니다.** ArraySize가 클수록 한 번에 더 많은 행을 실어 왕복이 감소합니다.
3. **스칼라 서브쿼리 캐싱은 반복 조회를 줄입니다.** 입력 값의 종류(distinct)가 적을수록(여기 40종) 캐시 히트로 서브쿼리 실행이 압축됩니다.
4. **두 최적화의 적용 대상이 다릅니다** — 왕복(네트워크)과 반복 실행(서브쿼리 블록). 효과를 서로 바꿔 말하면 처방이 어긋납니다.

📌 한 줄 정리: ArraySize는 1,500,000 ÷ (3,001−1) = 500이며, ArraySize를 키우면 Fetch 왕복이 줄고(Array Processing), 40종뿐인 dev_id는 스칼라 서브쿼리 캐싱으로 device 조회가 40회 수준으로 줄어듭니다 — 두 효과는 대상이 다릅니다.
