<!--meta
번호: 10
대상장: 4
대상절: 4.3
절제목: 해시 조인
문제유형: 적절하지_않은_것
보조자료: 실행계획
DBMS: 오라클
정답: 2
선택지유형: 코드형
함정유형: [값스왑]
대상개념: [해시_조인, 조인_방식_선택, Build_Input]
자극물밀도: 실행계획_pipe_역공학_4행
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 10

### 문제

해외송금 정산 배치가 대형 `해외송금거래`(약 6,800만 건)와 소형 `수취은행`(약 3,200건)을 **수취은행코드로 해시 조인**한다. 아래는 그 실행계획으로, `수취은행`(Id 2)이 첫 번째 자식으로 올라가 Build Input이 되고 `해외송금거래`(Id 3)가 두 번째 자식으로 Probe Input이 되었다. 이 실행계획(Build=수취은행, Probe=해외송금거래)을 **그대로 낼 수 있는 SQL·힌트로 가장 적절하지 <u>않은</u> 것은?**

#### [아 래]

```text
| Id  | Operation           | Name         |
|-----|---------------------|--------------|
|   0 | SELECT STATEMENT    |              |
|*  1 |  HASH JOIN          |              |
|   2 |   TABLE ACCESS FULL | 수취은행     |
|   3 |   TABLE ACCESS FULL | 해외송금거래 |
```

### 선택지

① 아래 힌트로 수취은행 b를 선행(build)에 두어 그대로 낸다.
```sql
SELECT /*+ LEADING(b t) USE_HASH(t) */
       b.수취은행명, t.송금액
  FROM 수취은행 b, 해외송금거래 t
 WHERE b.수취은행코드 = t.수취은행코드;
```

② 아래 힌트로 낸다.
```sql
SELECT /*+ LEADING(t b) USE_HASH(b) */
       b.수취은행명, t.송금액
  FROM 수취은행 b, 해외송금거래 t
 WHERE b.수취은행코드 = t.수취은행코드;
```

③ 아래 힌트로 낸다.
```sql
SELECT /*+ LEADING(t b) USE_HASH(b) SWAP_JOIN_INPUTS(b) */
       b.수취은행명, t.송금액
  FROM 수취은행 b, 해외송금거래 t
 WHERE b.수취은행코드 = t.수취은행코드;
```

④ 아래 힌트로 낸다.
```sql
SELECT /*+ LEADING(b t) USE_HASH(t) NO_SWAP_JOIN_INPUTS(t) */
       b.수취은행명, t.송금액
  FROM 수취은행 b, 해외송금거래 t
 WHERE b.수취은행코드 = t.수취은행코드;
```

---

### 정답 — ②

### 왜 ②인가

해시 조인 플랜에서 **첫 번째(위) 자식이 Build Input**이고 두 번째(아래) 자식이 Probe Input입니다. 이 플랜은 Id 2 `수취은행`이 첫 자식이므로 **Build=수취은행, Probe=해외송금거래**입니다. 이 방향을 결정하는 규칙 두 가지를 봅니다.

```text
규칙 1) LEADING의 선행(첫) 테이블이 기본적으로 Build Input이 된다.
규칙 2) SWAP_JOIN_INPUTS(x)는 x를 Build로 강제(기본 방향을 뒤집음),
        NO_SWAP_JOIN_INPUTS(x)는 x가 Build로 스왑되지 않게(Probe 유지) 한다.
```

각 선택지가 만들어 내는 Build 방향을 짚습니다.

```text
① LEADING(b t) USE_HASH(t)                        → 선행 b(수취은행)=Build          플랜과 일치  ✔
② LEADING(t b) USE_HASH(b)                        → 선행 t(해외송금거래)=Build, 스왑 없음  방향 반대  ✘
③ LEADING(t b) USE_HASH(b) SWAP_JOIN_INPUTS(b)    → 선행 t=Build이나 스왑으로 b=Build  일치  ✔
④ LEADING(b t) USE_HASH(t) NO_SWAP_JOIN_INPUTS(t) → 선행 b=Build, t는 Probe 고정        일치  ✔
```

②는 `LEADING(t b)`로 대형 `해외송금거래`를 선행에 두고 스왑 힌트가 없으므로 **Build=해외송금거래(대형)**가 되어, 플랜의 Build=수취은행(Id 2)과 **Build/Probe가 뒤바뀝니다**. 나머지 ①③④는 선행 지정이나 스왑으로 Build가 소형 `수취은행`이 되어 플랜과 같습니다. 따라서 이 플랜을 낼 수 없는, 가장 적절하지 <u>않은</u> 힌트는 ②입니다.

```text
플랜:  Build=수취은행(Id 2, 소형) / Probe=해외송금거래(Id 3, 대형)
②:    Build=해외송금거래(대형)    / Probe=수취은행(소형)   ← 두 입력을 맞바꾼 값스왑
```

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ○ | `LEADING(b t)`가 소형 수취은행 b를 선행에 두어 기본적으로 b가 Build가 되므로, Id 2(수취은행)=Build인 플랜을 그대로 냅니다 |
| ② | **✗** | `LEADING(t b)`로 대형 해외송금거래를 선행에 두고 SWAP_JOIN_INPUTS도 없어 Build=해외송금거래가 됩니다. 플랜은 Build=수취은행(Id 2)이므로 Build와 Probe를 맞바꾼 방향이라 이 플랜을 내지 못합니다 |
| ③ | ○ | `LEADING(t b)`면 기본 Build는 t지만 `SWAP_JOIN_INPUTS(b)`가 b(수취은행)를 Build로 강제하므로, 결과적으로 Id 2=수취은행=Build인 플랜과 일치합니다 |
| ④ | ○ | `LEADING(b t)`로 b=Build가 기본이고 `NO_SWAP_JOIN_INPUTS(t)`가 t를 Probe로 고정하므로, Build=수취은행·Probe=해외송금거래인 플랜을 그대로 냅니다 |

---

## ✅ 이 문제의 핵심

1. **해시 조인 플랜의 첫 자식 = Build Input, 둘째 자식 = Probe Input.** 이 플랜은 Id 2(수취은행)가 Build, Id 3(해외송금거래)가 Probe입니다.
2. **LEADING의 선행 테이블이 기본 Build**입니다. 방향을 뒤집으려면 `SWAP_JOIN_INPUTS`가 필요합니다.
3. **②는 대형을 선행에 두고 스왑이 없어 Build=대형** — 플랜(Build=소형)과 정반대라 이 플랜을 낼 수 없습니다.
4. **③·④는 스왑·비스왑 힌트로 Build를 소형으로 맞춘 서로 다른 표현**이라 모두 같은 플랜을 냅니다. Build/Probe를 맞바꾼 값스왑만 골라내야 합니다.

📌 한 줄 정리: 플랜의 첫 자식 Id 2가 수취은행이므로 Build=수취은행(소형)인데, ②는 `LEADING(t b)`로 대형 해외송금거래를 선행에 두고 스왑 힌트도 없어 Build=대형이 되어 Build/Probe가 뒤바뀌므로, 이 플랜을 내지 못하는 가장 적절하지 않은 힌트다.
