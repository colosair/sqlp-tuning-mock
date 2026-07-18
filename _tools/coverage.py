"""전 회차(N회차/문제/*.md)의 개념·절 커버리지를 누적 집계한다.

    python _tools/coverage.py            # 콘솔 요약
    python _tools/coverage.py --write    # 분석/커버리지_종합.md 갱신

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


if __name__ == "__main__":
    report()
