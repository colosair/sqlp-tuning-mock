"""생성 모의문항이 AGENTS.md 규약·품질 스펙을 지키는지 검증합니다.

    python _tools/verify.py [회차]      # 회차 기본값 1회차

노랭이 121 verify.py를 각색: 책 좌표 게이트를 빼고, 생성 문항용 게이트
(시대착오 가드·밀도 가드·clean-room 표식·분포)를 더했습니다.
"""

import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROUND = "1회차"
# 노랭이 저장소의 통제 어휘를 재사용(대상개념 검증). 경로가 없으면 태그 검사 건너뜀.
태그_사전 = ROOT.parent / "SQL 자격검정 실전문제 - 노랭이" / "분석" / "개념태그_사전.md"

CIRC = {"①": 1, "②": 2, "③": 3, "④": 4}
IDX = {v: k for k, v in CIRC.items()}

문제유형_값 = {"적절한_것", "적절하지_않은_것", "직접지목형"}
보조자료_값 = {"없음", "텍스트", "SQL", "실행계획", "트레이스", "표", "그림", "복합"}
DBMS_값 = {"오라클", "공통", "SQL_Server"}
선택지유형_값 = {"서술형", "코드형", "혼합"}
계산요구_값 = {"있음", "없음"}

# AGENTS.md 함정 카탈로그
함정_카탈로그 = {
    "정반대_진술", "같은것_다른이름", "하위항목_전체화", "범위밖_개념", "경계_오해",
    "원인_오귀속", "오라클↔SQLServer_뒤바꿈", "정규화_가정_오류", "별개_축_혼동",
    "반사적_연상", "핵심정리목록밖", "부분진실_형변환", "공통단서_무력화", "값스왑",
}

# ★ 시대착오 가드 — 노랭이가 안 쓰는 현대 실행계획 요소. [아 래] 박스에 있으면 실패.
시대착오_패턴 = re.compile(r"A-Rows|E-Rows|Buffers|Starts|Predicate Information|access\(|filter\(")
# 절대수식어 tell — 선택지에 과다하면 경고(난이도 저하)
절대수식어 = re.compile(r"항상|전혀|반드시|언제나|모두|절대")

TOTAL = 20  # 세트 문항 수


def 통제어휘():
    if not 태그_사전.exists():
        return None
    t = 태그_사전.read_text(encoding="utf-8")
    return {m.group(1) for m in re.finditer(r"^\| `([^`]+)` \|", t, re.M)}


def _dw(s):
    """디스플레이 폭. 굴림체는 W/F뿐 아니라 Ambiguous(A: → · ≠ ① 등)도 2배폭으로
    그린다(render.py `_dw()`와 같은 규칙 — 폰트 실측으로 확인)."""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F", "A") else 1 for c in s)


def 선택지폭(t):
    """선택지 4개의 표시 폭. 코드블록이 딸린 보기(역공학)는 코드까지 합산."""
    sec = t[t.find("### 선택지"):t.find("### 정답") if "### 정답" in t else len(t)]
    opts, cur, buf, fence = [], None, [], False
    for line in sec.split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
            buf.append(line)
            continue
        m = None if fence else re.match(r"^([①②③④])\s*(.*)$", line.strip())
        if m:
            if cur is not None:
                opts.append(cur + sum(_dw(c) for c in re.findall(r"```[a-z]*\n(.*?)\n```", "\n".join(buf), re.S)))
            cur, buf = _dw(re.sub(r"[*`]", "", m.group(2))), []
            continue
        buf.append(line)
    if cur is not None:
        opts.append(cur + sum(_dw(c) for c in re.findall(r"```[a-z]*\n(.*?)\n```", "\n".join(buf), re.S)))
    return opts


def 메타(t):
    m = re.search(r"<!--meta\n(.*?)\n-->", t, re.S)
    return dict(re.findall(r"^(\w+): (.+)$", m.group(1), re.M)) if m else None


def 리스트필드(v):
    return [x.strip() for x in (v or "[]").strip("[]").split(",") if x.strip()]


def main():
    round_name = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROUND
    round_dir = Path(round_name)
    if not round_dir.is_absolute():
        round_dir = ROOT / round_name
    문제_DIR = round_dir / "문제"
    if not 문제_DIR.exists():
        print(f"문제 디렉토리 없음: {문제_DIR}")
        sys.exit(1)
    print(f"검증 대상: {round_dir.name}\n")

    사전 = 통제어휘()
    errs, warns = [], []
    seen = {}
    rows = []
    길이통계 = []

    for f in sorted(문제_DIR.glob("mock-*.md")):
        t = f.read_text(encoding="utf-8")
        meta = 메타(t)
        rel = f.name
        if meta is None:
            errs.append(f"{rel}: meta 블록 없음")
            continue

        try:
            n, ans = int(meta["번호"]), int(meta["정답"])
        except (KeyError, ValueError) as e:
            errs.append(f"{rel}: 번호/정답 누락·형식 오류 ({e})")
            continue
        rows.append(meta)

        if n in seen:
            errs.append(f"{n}번 중복: {rel} / {seen[n]}")
        seen[n] = rel
        if f.name != f"mock-{n:02d}.md":
            errs.append(f"{rel}: 파일명이 번호({n})와 불일치")

        # 필수 필드
        for k in ["대상장", "대상절", "절제목", "자극물밀도", "출처"]:
            if k not in meta:
                errs.append(f"{n}번: 필수 메타 '{k}' 없음")
        if meta.get("출처") != "생성":
            errs.append(f"{n}번: 출처는 '생성'이어야 함 (clean-room 표식)")

        # 열거형
        for k, 허용 in [("문제유형", 문제유형_값), ("보조자료", 보조자료_값),
                        ("DBMS", DBMS_값), ("선택지유형", 선택지유형_값), ("계산요구", 계산요구_값)]:
            if meta.get(k) not in 허용:
                errs.append(f"{n}번: {k}={meta.get(k)!r} 허용값 아님 {sorted(허용)}")

        # 정답 자기정합: 헤딩 = 메타 = 오답표 볼드
        h = re.search(r"^### 정답 — ([①②③④])$", t, re.M)
        if not h:
            errs.append(f"{n}번: '### 정답 — ①' 헤딩 없음")
        elif CIRC[h.group(1)] != ans:
            errs.append(f"{n}번: 정답 헤딩({h.group(1)}) ≠ 메타({IDX.get(ans)})")

        # 선택지 4개
        sel = re.findall(r"^([①②③④]) ", t[t.find("### 선택지"):t.find("### 정답") if "### 정답" in t else len(t)], re.M)
        if sel != ["①", "②", "③", "④"]:
            errs.append(f"{n}번: 선택지가 ①②③④ 4개가 아님 ({sel})")

        # ★ 선택지 길이 편향 — '가장 긴 보기 = 정답'이면 자료를 안 보고도 찍힌다
        W = 선택지폭(t)
        if len(W) == 4 and sum(W):
            avg = sum(W) / 4
            ratio = W[ans - 1] / avg
            # 동률 최장은 단서가 아니다 — 다른 보기도 같은 폭이면 '가장 긴 것'을
            # 고르는 전략이 정답을 집어내지 못한다. 단독 최장일 때만 계상한다.
            longest = W[ans - 1] == max(W) and W.count(max(W)) == 1
            길이통계.append((n, longest, ratio, W[ans - 1]))
            if longest and ratio > 1.25:
                errs.append(f"{n}번: 정답이 최장이며 평균의 {ratio:.2f}배 "
                            f"({W[ans-1]}폭 vs 나머지 {[w for i,w in enumerate(W) if i!=ans-1]}) "
                            "— 길이만 보고 찍히므로 오답을 같은 밀도로 보강할 것")
            elif W[ans - 1] > 300:
                warns.append(f"{n}번: 정답 보기 {W[ans-1]}폭 — 근거 일부를 해설로 옮기는 편이 낫습니다")

        # 오답 이유 표
        tbl = re.findall(r"^\| ([①②③④]) \| (\S+) \|", t, re.M)
        if len(tbl) != 4:
            errs.append(f"{n}번: 오답 이유 표 {len(tbl)}행 (4행이어야 함)")
        elif [c for c, _ in tbl] != ["①", "②", "③", "④"]:
            errs.append(f"{n}번: 오답 표 순서가 ①②③④ 아님")
        else:
            bold = [c for c, v in tbl if v.startswith("**")]
            if len(bold) != 1:
                errs.append(f"{n}번: 굵은 판정 {len(bold)}개 (1개)")
            elif CIRC[bold[0]] != ans:
                errs.append(f"{n}번: 굵은 행({bold[0]}) ≠ 정답({IDX.get(ans)})")
            else:
                v = dict(tbl)[bold[0]]
                want = "**✗**" if meta.get("문제유형") == "적절하지_않은_것" else "**○**"
                if v != want:
                    errs.append(f"{n}번: 유형={meta.get('문제유형')}인데 정답 판정 {v} (기대 {want})")

        # 태그 / 함정
        tags = 리스트필드(meta.get("대상개념"))
        if not 1 <= len(tags) <= 5:
            errs.append(f"{n}번: 대상개념 {len(tags)}개 (1~5)")
        if 사전 is not None:
            for x in tags:
                if x not in 사전:
                    errs.append(f"{n}번: 대상개념 '{x}' 가 노랭이 태그 사전에 없음")
        for x in 리스트필드(meta.get("함정유형")):
            if x not in 함정_카탈로그:
                errs.append(f"{n}번: 함정유형 '{x}' 가 카탈로그에 없음")

        # 보조자료 ↔ [아 래] 정합
        box_present = "#### [아 래]" in t
        if (meta.get("보조자료") == "없음") == box_present:
            errs.append(f"{n}번: 보조자료={meta.get('보조자료')}인데 [아 래] 블록 유무 어긋남")

        # [아 래] 박스 내용 추출 (시대착오·밀도 가드용)
        box = ""
        if box_present:
            s = t.find("#### [아 래]")
            e = t.find("### 선택지", s)
            box = t[s:e]

        # ★ 시대착오 가드
        if box and 시대착오_패턴.search(box):
            bad = 시대착오_패턴.findall(box)
            errs.append(f"{n}번: [아 래]에 노랭이 미사용 현대 요소 {set(bad)} — 시대착오")

        # 밀도 가드
        밀도 = meta.get("자극물밀도", "")
        if "TKPROF" in 밀도:
            if not re.search(r"Count.*CPU.*Elapsed.*Disk.*Query.*Current.*Rows", box):
                errs.append(f"{n}번: 자극물밀도=TKPROF인데 Call 7열 표가 없음")
            if "RowSource" in 밀도 and "Row Source Operation" not in box:
                errs.append(f"{n}번: 자극물밀도=+RowSource인데 Row Source Operation 없음")
        if meta.get("계산요구") == "있음":
            why = t[t.find("### 왜"):t.find("### 오답 이유") if "### 오답 이유" in t else len(t)]
            if "```" not in why:
                errs.append(f"{n}번: 계산요구=있음인데 '### 왜'에 계산 블록(```)이 없음")

        # 절대수식어 tell 경보 (실패 아님)
        selblock = t[t.find("### 선택지"):t.find("### 정답") if "### 정답" in t else len(t)]
        cnt = len(절대수식어.findall(selblock))
        if cnt >= 3:
            warns.append(f"{n}번: 선택지 절대수식어 {cnt}회 — tell로 소거 쉬워질 수 있음(확인)")

        # 필수 절
        for sec in ["### 문제", "### 선택지", "### 오답 이유", "## ✅ 이 문제의 핵심"]:
            if sec not in t:
                errs.append(f"{n}번: '{sec}' 절 없음")
        if not re.search(r"^📌 한 줄 정리:", t, re.M):
            errs.append(f"{n}번: '📌 한 줄 정리:' 없음")

    # 전수 완비
    missing = [n for n in range(1, TOTAL + 1) if n not in seen]
    if missing:
        errs.append(f"누락 문항: {missing}")

    # 분포 확인 (경보)
    if len(rows) == TOTAL:
        def dist(k):
            return dict(Counter(r.get(k) for r in rows))
        ans_d = Counter(int(r["정답"]) for r in rows)
        밀도목록 = [r.get("자극물밀도", "") for r in rows]
        tk = sum(1 for d in 밀도목록 if "TKPROF" in d)
        plan = sum(1 for d in 밀도목록 if "실행계획" in d)
        box = sum(1 for r in rows if r.get("보조자료") != "없음")
        print("── 분포 ──")
        print("  문제유형:", dist("문제유형"))
        print("  정답    :", dict(sorted(ans_d.items())))
        print("  DBMS    :", dist("DBMS"))
        print(f"  [아 래] : {box}/{TOTAL} | TKPROF: {tk} | 실행계획: {plan} | 6.6: {'있음' if any(r.get('대상절')=='6.6' for r in rows) else '없음'}")
        if tk < 3:
            warns.append(f"밀도: TKPROF 트레이스 {tk}개 (품질 스펙 3~4 미달)")
        if plan < 2:
            warns.append(f"밀도: 실행계획 {plan}개 (품질 스펙 2~3 미달)")

        # ★ 회차 게이트 — 문항 게이트만으로는 "전부 1.05배로 최장"인 패턴을 못 막는다.
        #    '가장 긴 보기 = 정답'이 우연(25%=5문항)을 크게 넘으면 세트 전체가 찍힌다.
        lg = sum(1 for _, longest, _, _ in 길이통계 if longest)
        print(f"  최장=정답: {lg}/{len(길이통계)} (한도 8)")
        if lg > 8:
            errs.append(f"길이 편향: '가장 긴 보기 = 정답'이 {lg}/{TOTAL}문항 (한도 8) "
                        "— 자료를 읽지 않고 최장 보기만 골라도 맞는 세트가 됨")

        # ★ 정답 예측 패턴 가드 — 위치로 정답을 추정할 수 있는 규칙적 배열 차단
        ans_seq = [int(r["정답"]) for r in sorted(rows, key=lambda r: int(r["번호"]))]

        def _asc_run(s):  # 순환 오름(…4→1…) 최장 연속
            mx = run = 1
            for i in range(1, len(s)):
                run = run + 1 if s[i] == s[i - 1] % 4 + 1 else 1
                mx = max(mx, run)
            return mx

        def _same_run(s):
            mx = run = 1
            for i in range(1, len(s)):
                run = run + 1 if s[i] == s[i - 1] else 1
                mx = max(mx, run)
            return mx

        asc, same = _asc_run(ans_seq), _same_run(ans_seq)
        if asc >= 6 or same >= 4:
            errs.append(f"정답 배열이 예측 가능(순환오름런 {asc}·동일런 {same}) — 위치로 정답 추정 가능. 스크램블 필요: {ans_seq}")
        elif asc >= 4 or same >= 3:
            warns.append(f"정답 배열 규칙성(오름런 {asc}·동일런 {same}) — 스크램블 권장")

    print(f"\n문항 파일 {len(seen)}/{TOTAL}")
    if warns:
        print(f"\n경보 {len(warns)}건 (실패 아님, 확인):\n" + "\n".join(f"  ~ {w}" for w in warns))
    if errs:
        print(f"\n실패 {len(errs)}건\n" + "\n".join(f"  - {e}" for e in errs))
        sys.exit(1)
    print("\nPASS — 전 게이트 통과")


if __name__ == "__main__":
    main()
