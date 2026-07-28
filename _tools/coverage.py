"""전 회차(N회차/문제/*.md)의 개념·절 커버리지를 누적 집계한다.

    python _tools/coverage.py            # 콘솔 요약
    python _tools/coverage.py --write    # 분석/커버리지_종합.md 갱신
    python _tools/coverage.py --rounds   # N회차/커버리지.md 생성(3회차 이상)
    python _tools/coverage.py --index    # 분석/회차별_범위.md 생성
    python _tools/coverage.py --all      # 위 셋 모두

목적: "고빈도=반복, 저빈도·킬러=순회" 전략의 완성도를 정량 점검한다.
- 개념 × 회차 누적 매트릭스, 절별 커버 횟수
- 실제 121 빈도(있으면) 대비 반복 달성도, 잔여 미커버(freq≥2인데 0회)
- 회차별 사용 테이블명 목록(clean-room 중복 감사 보조)
"""

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
분석_DIR = ROOT / "분석"
빈도표 = ROOT.parent / "SQL 자격검정 실전문제 - 노랭이" / "분석" / "출제_스타일_분석.md"


def 회차목록():
    ds = sorted([p for p in ROOT.glob("*회차") if (p / "문제").is_dir()],
                key=lambda p: int(re.match(r"(\d+)", p.name).group(1)))
    return ds


def 메타(t):
    m = re.search(r"<!--meta\n(.*?)\n-->", t, re.S)
    return dict(re.findall(r"^(\w+): (.+)$", m.group(1), re.M)) if m else {}


def 리스트(v):
    return [x.strip() for x in (v or "[]").strip("[]").split(",") if x.strip()]


def 실제빈도():
    """출제_스타일_분석.md의 '반복 출제 개념' 표에서 개념→빈도. 없으면 빈 dict."""
    if not 빈도표.exists():
        return {}
    t = 빈도표.read_text(encoding="utf-8")
    freq = {}
    for m in re.finditer(r"^\| ([^|]+?) \| (\d+) \|$", t, re.M):
        name, n = m.group(1).strip(), int(m.group(2))
        if re.fullmatch(r"[\w가-힣_]+", name):
            freq[name] = n
    return freq


def 테이블명(t):
    """발문·SQL에서 테이블/도메인 후보를 폭넓게 수집(clean-room 감사 보조)."""
    names = set()
    # SQL의 FROM/JOIN/INTO/UPDATE 뒤 식별자
    for m in re.finditer(r"(?:FROM|JOIN|TABLE|INTO|UPDATE|MERGE\s+INTO)\s+`?([A-Za-z가-힣][\w가-힣]*)", t):
        names.add(m.group(1))
    # 백틱 인용 식별자(문항이 테이블명을 `…`로 표기) — 한글 2자+ 만
    for m in re.finditer(r"`([가-힣][\w가-힣]{1,})`", t):
        names.add(m.group(1))
    # 도메인성 접미사 명사
    for m in re.finditer(r"([가-힣]{2,}(?:내역|이력|정보|원장|로그|테이블|측정|상세|계약|접수|집계|마스터|현황|실적|기록|명세|대장))", t):
        names.add(m.group(1))
    # 대상개념·자극 키워드 등 흔한 기술어 제외
    stop = {"실행계획", "인덱스", "파티션", "트랜잭션", "옵티마이저", "히스토그램", "테이블"}
    return {n for n in names if n not in stop and len(n) >= 2}


def load_questions():
    """문항 1건 = dict. 회차별 커버리지·범위 색인의 공통 입력."""
    rows = []
    for d in 회차목록():
        rn = int(re.match(r"(\d+)", d.name).group(1))
        for f in sorted((d / "문제").glob("mock-*.md"),
                        key=lambda p: int(re.search(r"mock-(\d+)", p.name).group(1))):
            m = 메타(f.read_text(encoding="utf-8"))
            rows.append({
                "회차": rn, "번호": int(m["번호"]), "장": m.get("대상장"), "절": m.get("대상절"),
                "절제목": m.get("절제목", ""), "문제유형": m.get("문제유형"), "DBMS": m.get("DBMS"),
                "정답": int(m["정답"]), "보조자료": m.get("보조자료"), "자극물밀도": m.get("자극물밀도", ""),
                "계산요구": m.get("계산요구"), "대상개념": 리스트(m.get("대상개념")),
                "함정유형": 리스트(m.get("함정유형")),
            })
    return rows


def canonical_titles(rows):
    """절 번호별 정준 절제목(최빈) + 변형 목록. 문항 md는 고치지 않고 표시만 통일한다."""
    by = defaultdict(Counter)
    for r in rows:
        by[r["절"]][r["절제목"]] += 1
    canon = {s: c.most_common(1)[0][0] for s, c in by.items()}
    variants = {s: c for s, c in by.items() if len(c) > 1}
    return canon, variants


def 절정렬(s):
    return [int(x) for x in re.findall(r"\d+", s)] or [99]


def 자극물집계(rs):
    """자극물밀도 문자열에서 유형별 개수."""
    g = lambda pred: sum(1 for r in rs if pred(r["자극물밀도"]))
    return {
        "박스": sum(1 for r in rs if r["보조자료"] != "없음"),
        "TKPROF": g(lambda d: "TKPROF" in d),
        "실행계획": g(lambda d: "실행계획" in d),
        "표": g(lambda d: d in ("Lock표", "TXxt표", "표")),
        "DDL": g(lambda d: "DDL" in d),
        "SQL": g(lambda d: d == "SQL"),
        "계산": sum(1 for r in rs if r["계산요구"] == "있음"),
    }


def 특징태그(rs):
    """자극물밀도 값에서 그 회차의 특징을 기계 추출(설계 의도 산문은 쓰지 않는다)."""
    tags = []
    d = [r["자극물밀도"] for r in rs]
    if any("역공학" in x for x in d):
        tags.append("실행계획 역공학")
    par = [x for x in d if "병렬" in x]
    if par:
        n = max((int(m.group(1)) for x in par for m in [re.search(r"(\d+)행", x)] if m), default=0)
        tags.append(f"병렬 플랜{f' {n}행+' if n else ''}")
    if any("TKPROF" in x and "RowSource" in x for x in d):
        tags.append("TKPROF+RowSource")
    if any("DDL" in x for x in d):
        tags.append("파티션 DDL")
    if sum(1 for r in rs if r["계산요구"] == "있음") >= 5:
        tags.append("계산 강화")
    return " · ".join(tags) or "—"


def write_round_docs(rows, canon, only_missing=True):
    """N회차/커버리지.md 생성. 기본은 3회차 이상만(1·2회차 수기 문서 보호)."""
    made = []
    rounds = sorted({r["회차"] for r in rows})
    for rn in rounds:
        path = ROOT / f"{rn}회차" / "커버리지.md"
        if only_missing and rn <= 2:
            continue
        rs = [r for r in rows if r["회차"] == rn]
        prev_secs = {r["절"] for r in rows if r["회차"] < rn}
        new_secs = sorted({r["절"] for r in rs} - prev_secs, key=절정렬)
        st = 자극물집계(rs)
        concepts = Counter(c for r in rs for c in r["대상개념"])
        traps = Counter(t for r in rs for t in r["함정유형"])
        L = [f"# 커버리지 — SQLP 과목 III 튜닝 스타일 모의문제 · {rn}회차 20선", "",
             f"총 **{len(rs)}문항**({rn}회차). 아래는 이 세트가 커버한 개념·함정·분포·자극물 밀도 요약입니다"
             f"(`_tools/coverage.py`가 문항 메타에서 자동 생성).", "",
             "## 문항 일람", "",
             "| # | 대상장.절 | 절제목 | 유형 | 자극물밀도 | 정답 | 대상개념 |",
             "|--:|---|---|---|---|:-:|---|"]
        for r in rs:
            L.append(f"| {r['번호']} | {r['절']} | {canon[r['절']]} | {r['문제유형'].replace('_', ' ')} | "
                     f"{r['자극물밀도']} | {'①②③④'[r['정답']-1]} | {', '.join(r['대상개념'])} |")
        def dist(k, order=None):
            c = Counter(r[k] for r in rs)
            keys = order or sorted(c, key=lambda x: -c[x])
            return " · ".join(f"{k2.replace('_',' ')} {c[k2]}" for k2 in keys if c.get(k2))
        L += ["", "### 문제유형", "", dist("문제유형", ["적절한_것", "적절하지_않은_것", "직접지목형"]),
              "", "### DBMS", "", dist("DBMS", ["오라클", "공통", "SQL_Server"]),
              "", "### 정답 번호", "",
              " · ".join(f"{'①②③④'[i]} {sum(1 for r in rs if r['정답']==i+1)}" for i in range(4)),
              "", "### 장 분포", "",
              " · ".join(f"제{c} {n}" for c, n in sorted(Counter(r["장"] for r in rs).items())),
              "", "### 자극물 밀도", "",
              f"- [아 래] 박스: **{st['박스']}/{len(rs)}**",
              f"- 정통 TKPROF 트레이스: **{st['TKPROF']}**",
              f"- 구식 포맷 실행계획: **{st['실행계획']}**",
              f"- 세션/Lock·타임라인 표: {st['표']}",
              f"- 다분할 파티션 DDL: {st['DDL']}",
              f"- SQL 지문: {st['SQL']}",
              f"- 계산·수치 판정 강제: **{st['계산']}**",
              "", "### 함정 유형 분포", "",
              " · ".join(f"{t} {n}" for t, n in traps.most_common())]
        if new_secs:
            L += ["", f"### 직전 회차까지 대비 신규 커버 절", "",
                  " · ".join(f"{s} {canon[s]}" for s in new_secs)]
        L += ["", f"### 대상 개념 ({len(concepts)}종)", "",
              ", ".join(f"{c}({n})" if n > 1 else c for c, n in concepts.most_common()),
              "", "---", "",
              "모든 문항은 명시 정답을 독립 에이전트가 직접 풀어 **정답 유일성·오답 타당성·수치 정합**을 "
              "검증했습니다. 실행계획은 A-Rows/Buffers/Predicate Information 같은 현대 요소를 쓰지 않는 "
              "구식 포맷입니다.", ""]
        path.write_text("\n".join(L), encoding="utf-8")
        made.append(str(path.relative_to(ROOT)))
    return made


def write_index(rows, canon, variants):
    """분석/회차별_범위.md — 절 기준 학습 동선 색인."""
    rounds = sorted({r["회차"] for r in rows})
    secs = sorted({r["절"] for r in rows}, key=절정렬)
    L = [f"# 회차별 출제·학습 범위 색인 ({len(rounds)}개 회차 · {len(rows)}문항)", "",
         "문항 메타(`대상절`·`자극물밀도`·`계산요구` 등)에서 **자동 생성**됩니다"
         "(`python _tools/coverage.py --index`). 개념 축 집계는 "
         "[커버리지_종합.md](커버리지_종합.md)를 보세요.", "",
         "## 회차 요약", "",
         "| 회차 | 단계 | 장 분포(1~7) | 다룬 절 | 신규 커버 절 | TKPROF | 실행계획 | 표 | DDL | 계산 | 특징 |",
         "|--:|---|---|--:|---|--:|--:|--:|--:|--:|---|"]
    for rn in rounds:
        rs = [r for r in rows if r["회차"] == rn]
        st = 자극물집계(rs)
        ch = Counter(r["장"] for r in rs)
        prev = {r["절"] for r in rows if r["회차"] < rn}
        new = sorted({r["절"] for r in rs} - prev, key=절정렬)
        L.append(f"| {rn} | {'A(정착)' if rn <= 6 else 'B(실전)'} | "
                 f"{'·'.join(str(ch.get(str(c), 0)) for c in range(1, 8))} | "
                 f"{len({r['절'] for r in rs})} | {' '.join(new) if new else '—'} | "
                 f"{st['TKPROF']} | {st['실행계획']} | {st['표']} | {st['DDL']} | {st['계산']} | {특징태그(rs)} |")
    L += ["", "> 단계: **A(1~6회차)** 빈출 개념 반복 + 전 범위 순회 · **B(7~12회차)** 실전 상향"
          "(역공학·복합 지문·킬러 유형).", "",
          "## 절 × 회차 매트릭스", "",
          "셀 = 그 회차에서 그 절을 다룬 문항 수. **이 절을 공부하려면 어느 회차를 풀면 되는지** 바로 찾습니다.", "",
          "| 절 | 절제목 | " + " | ".join(f"{r}회" for r in rounds) + " | 계 |",
          "|---|---|" + "--:|" * (len(rounds) + 1)]
    grand = 0
    for s in secs:
        cells = [sum(1 for r in rows if r["회차"] == rn and r["절"] == s) for rn in rounds]
        grand += sum(cells)
        L.append(f"| {s} | {canon[s]} | " + " | ".join(str(c) if c else "·" for c in cells) + f" | **{sum(cells)}** |")
    L += [f"| **계** | | " + " | ".join(str(sum(1 for r in rows if r['회차'] == rn)) for rn in rounds) + f" | **{grand}** |",
          "", "## 절별 수록 회차", "",
          "| 절 | 절제목 | 수록 회차 |", "|---|---|---|"]
    for s in secs:
        rr = sorted({r["회차"] for r in rows if r["절"] == s})
        L.append(f"| {s} | {canon[s]} | {', '.join(f'{x}회차' for x in rr)} |")
    if variants:
        L += ["", "---", "",
              f"> **표기 참고**: 문항 메타의 `절제목`이 {len(variants)}개 절에서 갈립니다"
              "(초기 회차가 부제를 붙인 흔적). 이 문서는 절 번호별 **최빈 제목을 정준**으로 씁니다 — "
              "문항 md는 수정하지 않았습니다.", ""]
    path = 분석_DIR / "회차별_범위.md"
    path.write_text("\n".join(L), encoding="utf-8")
    return path


def collect():
    rounds = 회차목록()
    per_round = {}
    concept_rounds = defaultdict(list)   # 개념 -> [회차숫자...]
    sect = Counter()
    concept_total = Counter()
    tables = {}
    for d in rounds:
        rn = int(re.match(r"(\d+)", d.name).group(1))
        c = Counter()
        tbl = set()
        files = sorted((d / "문제").glob("mock-*.md"))
        for f in files:
            t = f.read_text(encoding="utf-8")
            m = 메타(t)
            for x in 리스트(m.get("대상개념")):
                c[x] += 1
                concept_total[x] += 1
            concept_rounds_seen = set(리스트(m.get("대상개념")))
            for x in concept_rounds_seen:
                concept_rounds[x].append(rn)
            sect[m.get("대상절", "?")] += 1
            tbl |= 테이블명(t)
        per_round[rn] = {"n": len(files), "concepts": c}
        tables[rn] = sorted(tbl)
    return rounds, per_round, concept_rounds, sect, concept_total, tables


def report():
    rounds, per_round, concept_rounds, sect, concept_total, tables = collect()
    freq = 실제빈도()
    lines = []
    rn_list = sorted(per_round)
    total_q = sum(v["n"] for v in per_round.values())
    lines.append(f"# 누적 커버리지 종합 ({len(rn_list)}개 회차 · {total_q}문항)\n")
    lines.append("회차: " + ", ".join(f"{r}회차({per_round[r]['n']})" for r in rn_list) + "\n")

    # 고빈도 반복 달성도
    if freq:
        lines.append("## 고빈도 개념 반복 달성도 (실제 121 빈도 대비 누적 출제)\n")
        lines.append("| 개념 | 실제빈도 | 누적출제 | 등장회차 |")
        lines.append("|---|--:|--:|---|")
        for name, fq in sorted(freq.items(), key=lambda kv: -kv[1]):
            if fq < 3:
                continue
            got = concept_total.get(name, 0)
            rs = ",".join(map(str, sorted(concept_rounds.get(name, []))))
            flag = " ⚠️" if got < max(2, fq // 2) else ""
            lines.append(f"| {name} | {fq} | {got} | {rs or '-'}{flag}")
        lines.append("")

    # 절 커버
    lines.append("## 절별 누적 커버 횟수\n")
    lines.append("| 절 | 횟수 |")
    lines.append("|---|--:|")
    for s in sorted(sect, key=lambda x: [int(y) for y in re.findall(r"\d+", x)] or [99]):
        lines.append(f"| {s} | {sect[s]} |")
    lines.append("")

    # 잔여 미커버 (freq>=2 인데 0회)
    if freq:
        미커버 = [n for n, fq in freq.items() if fq >= 2 and concept_total.get(n, 0) == 0]
        lines.append(f"## 잔여 미커버 (실제 freq≥2 · 누적 0회) — {len(미커버)}종\n")
        lines.append(", ".join(sorted(미커버)) if 미커버 else "**없음 — freq≥2 개념 전부 커버**")
        lines.append("")

    # 테이블명(clean-room)
    lines.append("## 회차별 사용 테이블명 (clean-room 중복 감사)\n")
    for r in rn_list:
        lines.append(f"- **{r}회차**: {', '.join(tables[r]) or '-'}")
    lines.append("")

    text = "\n".join(lines)
    if "--write" in sys.argv:
        분석_DIR.mkdir(exist_ok=True)
        (분석_DIR / "커버리지_종합.md").write_text(text, encoding="utf-8")
        print(f"작성: {분석_DIR / '커버리지_종합.md'}")
    print(text)


def main():
    a = sys.argv[1:]
    allf = "--all" in a
    if allf or "--rounds" in a or "--index" in a:
        rows = load_questions()
        canon, variants = canonical_titles(rows)
        if allf or "--rounds" in a:
            made = write_round_docs(rows, canon, only_missing="--force" not in a)
            print(f"회차별 커버리지 {len(made)}건 작성: {', '.join(made) if made else '(없음)'}")
        if allf or "--index" in a:
            print(f"작성: {write_index(rows, canon, variants)}")
        if variants:
            print(f"\n[알림] 절제목 표기가 갈리는 절 {len(variants)}개 — "
                  "산출물은 최빈 제목으로 정준화(문항 md 무수정):")
            for s in sorted(variants, key=절정렬):
                print(f"   {s}: " + " / ".join(f"{k}({v})" for k, v in variants[s].most_common()))
    if allf or "--write" in a or not a:
        report()


if __name__ == "__main__":
    main()
