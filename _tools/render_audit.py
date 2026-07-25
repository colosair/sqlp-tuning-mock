"""md 문항의 모든 자료가 PDF에 실렸는지 대조한다(렌더러 회귀 방지).

    python _tools/render_audit.py            # 전 회차
    python _tools/render_audit.py 2회차 7회차  # 특정 회차

검사: [아 래] 박스의 **모든** 코드블록 / 발문 코드블록 / 선택지 4개의 lead·코드블록
      / '✅ 이 문제의 핵심' / 오답표 4행 / 한 줄 정리.

※ 오탐 회피 3원칙 (이걸 지키지 않으면 결과를 신뢰할 수 없다)
  1. 여러 줄을 이어 붙인 키를 쓰지 않는다 — 블록이 페이지 경계에서 갈리면 오탐.
     → **줄 단위**로 대조하고 블록의 hit 비율로 판정한다.
  2. mono(굴림체) 한글이 PDF 추출에서 유실될 수 있다 → 한글 키가 실패하면
     **ASCII 전용 키**로 2차 확인한다.
  3. 짧은 플랜 행(`| 0 | SELECT STATEMENT |`)은 문항 간 중복이라 단독 근거가 못 된다
     → 긴 줄(변별력 있는 줄) 위주로 보고, 0% 일치일 때만 누락으로 확정한다.
"""

import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent
FENCE = r"```[a-z]*\n(.*?)\n```"


def alnum(s):
    return re.sub(r"[^0-9A-Za-z가-힣]", "", s)


def ascii_only(s):
    return re.sub(r"[^0-9A-Za-z]", "", s)


def split_sections(body):
    """render.py와 동일한 펜스 인식 섹션 분할."""
    secs, cur, buf, fence = {}, None, [], False
    for line in body.split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
            buf.append(line)
            continue
        if not fence:
            h = re.match(r"^#+ (.+?)\s*$", line)
            if h:
                if cur is not None:
                    secs[cur] = "\n".join(buf).strip("\n")
                cur, buf = h.group(1).strip(), []
                continue
            if line.strip() == "---":
                if cur is not None:
                    secs[cur] = "\n".join(buf).strip("\n")
                    cur, buf = None, []
                continue
        buf.append(line)
    if cur is not None:
        secs[cur] = "\n".join(buf).strip("\n")
    return secs


def present(text, pdf_a, pdf_s, minlen=12):
    """한 줄이 PDF에 있는가 — 한글 키 → 실패 시 ASCII 키로 2차 확인."""
    ka = alnum(text)
    if len(ka) < 6:
        return None                      # 너무 짧은 줄은 판정 보류(변별력 없음)
    if ka[:minlen] in pdf_a:
        return True
    ks = ascii_only(text)
    if len(ks) >= 8 and ks[:minlen] in pdf_s:
        return True                      # mono 한글 추출 유실 케이스
    return False


def block_gap(code, pdf_a, pdf_s):
    """블록의 실질 행 중 PDF에서 못 찾은 수 → (miss, total).

    줄 단위 대조라 페이지 분할로는 miss가 나지 않는다. 반대로 짧은 행은 다른
    문항과 문자열이 겹쳐 '거짓 hit'가 날 수 있으므로, **거짓 miss는 없다**는
    성질을 이용해 miss가 1건이라도 있으면 보고한다(민감도 우선)."""
    lines = [l for l in code.split("\n")
             if alnum(l) and not set(l.strip()) <= set("-|+: ")]
    judged = [present(l, pdf_a, pdf_s) for l in lines]
    judged = [j for j in judged if j is not None]
    return sum(1 for j in judged if not j), len(judged)


def audit_round(rd):
    pdfs = sorted((ROOT / rd).glob("*.pdf"))
    if not pdfs:
        return [f"{rd}: PDF 없음"]
    raw = "".join(p.get_text() for p in fitz.open(pdfs[0]))
    pdf_a, pdf_s = alnum(raw), ascii_only(raw)
    probs = []
    files = sorted((ROOT / rd / "문제").glob("mock-*.md"),
                   key=lambda p: int(re.search(r"mock-(\d+)", p.name).group(1)))
    for f in files:
        t = f.read_text(encoding="utf-8")
        sec = split_sections(t[t.find("-->") + 3:])
        tag = f"{rd} {f.stem}"

        for i, code in enumerate(re.findall(FENCE, sec.get("[아 래]", ""), re.S), 1):
            miss, tot = block_gap(code, pdf_a, pdf_s)
            if miss:
                probs.append(f"{tag}: [아 래] 코드블록#{i} {miss}/{tot}행 누락")
        for i, code in enumerate(re.findall(FENCE, sec.get("문제", ""), re.S), 1):
            miss, tot = block_gap(code, pdf_a, pdf_s)
            if miss:
                probs.append(f"{tag}: 발문 코드블록#{i} {miss}/{tot}행 누락")

        sel = sec.get("선택지", "")
        marks = re.findall(r"^([①②③④])\s*(.*)$", sel, re.M)
        if len(marks) != 4:
            probs.append(f"{tag}: 선택지 {len(marks)}개(4개여야 함)")
        for mark, lead in marks:
            if present(lead, pdf_a, pdf_s) is False:
                probs.append(f"{tag}: 선택지 {mark} 문장 누락")
        for i, code in enumerate(re.findall(FENCE, sel, re.S), 1):
            miss, tot = block_gap(code, pdf_a, pdf_s)
            if miss:
                probs.append(f"{tag}: 선택지 코드블록#{i} {miss}/{tot}행 누락")

        kk = next((k for k in sec if "이 문제의 핵심" in k), None)
        if kk:
            body = [l for l in sec[kk].split("\n")
                    if alnum(l) and not l.lstrip().startswith("📌")]
            judged = [present(re.sub(r"[*`]", "", l), pdf_a, pdf_s) for l in body]
            judged = [j for j in judged if j is not None]
            if judged and not any(judged):
                probs.append(f"{tag}: '이 문제의 핵심' 누락")

        oab = re.findall(r"^\| ([①②③④]) \| (\S+) \| (.+?) \|$", sec.get("오답 이유", ""), re.M)
        if len(oab) != 4:
            probs.append(f"{tag}: 오답표 렌더 정규식 {len(oab)}/4 → PDF 표 누락 위험")

        m = re.search(r"^📌 한 줄 정리: (.+)$", t, re.M)
        if m and present(m.group(1), pdf_a, pdf_s) is False:
            probs.append(f"{tag}: 한 줄 정리 누락")
    return probs


def main():
    rounds = sys.argv[1:] or sorted(
        (p.name for p in ROOT.glob("*회차") if (p / "문제").is_dir()),
        key=lambda n: int(re.match(r"(\d+)", n).group(1)))
    total = 0
    for rd in rounds:
        probs = audit_round(rd)
        total += len(probs)
        print(f"── {rd}: {'누락 없음' if not probs else f'{len(probs)}건'}")
        for p in probs:
            print(f"   ✗ {p}")
    print(f"\n{'PASS — 전 회차 md 자료가 PDF에 모두 실렸습니다' if total == 0 else f'FAIL — 총 {total}건'}")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
