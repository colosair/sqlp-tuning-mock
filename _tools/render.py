"""rich md(문제/mock-*.md)를 직접 읽어 노랭이 룩 시험지 PDF를 만듭니다.

    python _tools/render.py [회차] [출력.pdf]      # 회차 기본값 1회차

중간 DSL을 거치지 않고 md를 파싱합니다. 실행계획·TKPROF 표의 ASCII 정렬을
위해 한글이 정확히 2배폭인 고정폭 폰트(굴림체, gulim.ttc subfontIndex=1)를
씁니다. 폰트 경로는 아래 상수로 자족.
"""

import html
import re
import sys
import unicodedata
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable, KeepTogether, PageBreak, Paragraph, Preformatted,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)

FONT_REGULAR = r"C:\Windows\Fonts\NotoSansKR-Regular.ttf"
FONT_BOLD = r"C:\Windows\Fonts\NotoSansKR-Bold.ttf"
FONT_MONO = r"C:\Windows\Fonts\gulim.ttc"
FONT_MONO_SUBFONT = 1  # 0=굴림 1=굴림체(고정폭)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROUND = "1회차"

A4W, A4H = A4
LM = RM = 18 * mm
CONTENT = A4W - LM - RM
NUMW = 13 * mm
IND = 13 * mm
OPT_HANG = 5 * mm

DARK = colors.HexColor("#3a3a3a")
GRAY = colors.HexColor("#8a8a8a")
LIGHTBG = colors.HexColor("#f5f5f3")
ACCENT = colors.HexColor("#c0392b")
S = {}


def register():
    pdfmetrics.registerFont(TTFont("KR", FONT_REGULAR))
    pdfmetrics.registerFont(TTFont("KR-B", FONT_BOLD))
    pdfmetrics.registerFont(TTFont("Mono", FONT_MONO, subfontIndex=FONT_MONO_SUBFONT))


def styles():
    S["title"] = ParagraphStyle("title", fontName="KR-B", fontSize=16, leading=22, alignment=TA_CENTER)
    S["intro"] = ParagraphStyle("intro", fontName="KR", fontSize=9, leading=14, alignment=TA_CENTER, textColor=GRAY)
    S["num"] = ParagraphStyle("num", fontName="KR-B", fontSize=10.5, leading=12, alignment=TA_CENTER)
    S["stem"] = ParagraphStyle("stem", fontName="KR-B", fontSize=10.3, leading=15.5)
    S["opt"] = ParagraphStyle("opt", fontName="KR", fontSize=9.8, leading=14.6,
                              leftIndent=IND + OPT_HANG, firstLineIndent=-OPT_HANG, spaceAfter=1.2)
    S["boxtitle"] = ParagraphStyle("boxtitle", fontName="KR-B", fontSize=8.5, leading=11, alignment=TA_CENTER, textColor=colors.white)
    S["mono"] = ParagraphStyle("mono", fontName="Mono", fontSize=7.6, leading=10.4)
    S["anshdr"] = ParagraphStyle("anshdr", fontName="KR-B", fontSize=13, leading=18, spaceAfter=6)
    S["gridcap"] = ParagraphStyle("gridcap", fontName="KR-B", fontSize=10.5, leading=15, spaceBefore=2, spaceAfter=4)
    S["gridcell"] = ParagraphStyle("gridcell", fontName="KR", fontSize=9.2, leading=12, alignment=TA_CENTER)
    S["ans_hd"] = ParagraphStyle("ans_hd", fontName="KR-B", fontSize=10.4, leading=15, textColor=DARK, spaceBefore=8, spaceAfter=2.5)
    S["ans_hd2"] = ParagraphStyle("ans_hd2", fontName="KR-B", fontSize=9.4, leading=13.5, textColor=DARK, leftIndent=6 * mm, spaceBefore=1, spaceAfter=1.5)
    S["why"] = ParagraphStyle("why", fontName="KR", fontSize=9.2, leading=13.6, leftIndent=6 * mm, spaceAfter=2.5)
    S["cell"] = ParagraphStyle("cell", fontName="KR", fontSize=8.6, leading=12)
    S["cellc"] = ParagraphStyle("cellc", fontName="KR-B", fontSize=8.6, leading=12, alignment=TA_CENTER)


def esc(t):
    t = t.replace("<u>", "\x00U\x00").replace("</u>", "\x00u\x00")
    t = html.escape(t)
    t = t.replace("\x00U\x00", "<u>").replace("\x00u\x00", "</u>")
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`([^`]+)`", r"<font name='KR-B'>\1</font>", t)
    return t


def esc_plain(t):
    """보기(선택지)용 — 볼드를 만들지 않는다. `코드`·**강조** 마커는 제거만."""
    t = t.replace("<u>", "\x00U\x00").replace("</u>", "\x00u\x00")
    t = html.escape(t)
    t = t.replace("\x00U\x00", "<u>").replace("\x00u\x00", "</u>")
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    return t


def _dw(s):
    """디스플레이 폭. 굴림체 고정폭에서 동아시아 폭(W/F) 문자는 정확히 2배."""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in s)


def _is_div(s):
    b = s.strip()
    return b != "" and set(b) <= set("-:+ ")


def _pipe_block(rows_txt):
    """`|` 구분 표를 디스플레이 폭 기준으로 재정렬(한글=2배폭 보정)."""
    rows = [ln.split("|") for ln in rows_txt]
    ncol = max(len(r) for r in rows)
    for r in rows:
        r += [""] * (ncol - len(r))
    div = ["".join(r) and _is_div("".join(r)) for r in rows]
    widths = [0] * ncol
    for r, d in zip(rows, div):
        if d:
            continue
        for i, c in enumerate(r):
            widths[i] = max(widths[i], _dw(c.rstrip()))
    out = []
    for r, d in zip(rows, div):
        cells = []
        for i, c in enumerate(r):
            if i == 0 or i == ncol - 1:
                cells.append(c)                      # 바깥 여백·들여쓰기 보존
            elif d:
                cells.append("-" * widths[i])
            else:
                body = c.rstrip()
                cells.append(body + " " * (widths[i] - _dw(body)))
        out.append("|".join(cells))
    return out


def _realign_pipes(lines):
    out, block = [], []

    def flush():
        out.extend(_pipe_block(block) if len(block) >= 2 else block)
        block.clear()

    for ln in lines:
        if "|" in ln:
            block.append(ln)
        else:
            flush()
            out.append(ln)
    flush()
    return "\n".join(out)


def _is_paren_plan(lines):
    has_hdr = any("(" in ln and re.search(r"Cost|COST|Card|CARD|Bytes|BYTES", ln) for ln in lines)
    data = sum(1 for ln in lines if ln.rstrip().endswith(")") and "=" not in ln)
    return has_hdr and data >= 2


def _realign_paren(lines):
    """구식 들여쓰기 트리(`… ( Cost Card Bytes )`)에서 `(` 열을 세로로 맞춘다."""
    idx = [ln.rfind("(") for ln in lines]
    maxw = max((_dw(ln[:i].rstrip()) for ln, i in zip(lines, idx) if i >= 0), default=0)
    rebuilt, total = [], 0
    for ln, i in zip(lines, idx):
        if i < 0:
            rebuilt.append(None)
        else:
            left = ln[:i].rstrip()
            r = left + " " * (maxw - _dw(left)) + " " + ln[i:].rstrip()
            rebuilt.append(r)
            total = max(total, _dw(r))
    out = []
    for r, ln in zip(rebuilt, lines):
        if r is not None:
            out.append(r)
        elif _is_div(ln):
            out.append("-" * total)
        else:
            out.append(ln)
    return "\n".join(out)


def realign_box(code):
    """실행계획/표 박스의 ASCII 정렬을 디스플레이 폭 기준으로 재계산.

    한글은 굴림체에서 2배폭이라, 글자 수로 맞춘 소스는 한글 셀 뒤 열이 밀린다.
    파이프 표와 구식 괄호 트리를 자동 교정하고, 그 외(TKPROF·타임라인 등
    한글이 행 끝에 오는 표)는 손대지 않는다."""
    lines = code.split("\n")
    if any("|" in ln for ln in lines):
        return _realign_pipes(lines)
    if _is_paren_plan(lines):
        return _realign_paren(lines)
    return code


def num_box(n):
    cell = Table([[Paragraph(str(n), S["num"])]], colWidths=[9.5 * mm], rowHeights=[7 * mm])
    cell.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.9, DARK), ("ROUNDEDCORNERS", [3, 3, 3, 3]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return cell


def mono_flowables(codes, gap=2 * mm):
    """코드블록 리스트 → Preformatted 리스트(블록 사이 여백).

    realign_box는 **블록마다 개별** 적용한다. 합쳐서 정렬하면 파이프 재정렬기가
    SQL 줄까지 표로 오인한다."""
    flow = []
    for i, code in enumerate(codes):
        if i:
            flow.append(Spacer(1, gap))
        flow.append(Preformatted(realign_box(code.strip("\n")), S["mono"], maxLineLength=130))
    return flow


def code_panel(codes, indent=IND):
    """리본 없는 연회색 mono 패널(발문·선택지 안의 코드블록용)."""
    if isinstance(codes, str):
        codes = [codes]
    inner = Table([[mono_flowables(codes)]], colWidths=[CONTENT - indent])
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHTBG), ("BOX", (0, 0), (-1, -1), 0.5, GRAY),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    outer = Table([["", inner]], colWidths=[indent, CONTENT - indent])
    outer.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                               ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                               ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return outer


def below_box(codes):
    """「아 래」 박스 — 박스 안의 **모든** 코드블록을 리본 하나 아래 쌓는다."""
    if isinstance(codes, str):
        codes = [codes]
    ribbon = Table([[Paragraph("아 래", S["boxtitle"])]], colWidths=[20 * mm], rowHeights=[5.4 * mm])
    ribbon.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), DARK), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    body = mono_flowables(codes)
    inner = Table([[ribbon], [body]], colWidths=[CONTENT - IND])
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0, 1), (0, 1), LIGHTBG), ("BOX", (0, 0), (-1, -1), 0.5, GRAY),
        ("LEFTPADDING", (0, 0), (-1, 0), 3), ("TOPPADDING", (0, 0), (-1, 0), 2), ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("LEFTPADDING", (0, 1), (0, 1), 8), ("RIGHTPADDING", (0, 1), (0, 1), 6),
        ("TOPPADDING", (0, 1), (0, 1), 6), ("BOTTOMPADDING", (0, 1), (0, 1), 6)]))
    outer = Table([["", inner]], colWidths=[IND, CONTENT - IND])
    outer.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                               ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                               ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return outer


def split_sections(body):
    """펜스(```)를 인식하며 헤딩 단위로 분할. {정확한 헤딩 텍스트: 본문}.
    바깥의 `---`는 종결자로만 쓰고, 펜스 안의 `----`는 무시한다."""
    sections, cur, buf, in_fence = {}, None, [], False
    for line in body.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            buf.append(line)
            continue
        if not in_fence:
            h = re.match(r"^#+ (.+?)\s*$", line)
            if h:
                if cur is not None:
                    sections[cur] = "\n".join(buf).strip("\n")
                cur, buf = h.group(1).strip(), []
                continue
            if line.strip() == "---":  # 바깥 구분선 = 현재 섹션 종료
                if cur is not None:
                    sections[cur] = "\n".join(buf).strip("\n")
                    cur, buf = None, []
                continue
        buf.append(line)
    if cur is not None:
        sections[cur] = "\n".join(buf).strip("\n")
    return sections


FENCE = r"```[a-z]*\n(.*?)\n```"


def all_code_blocks(block):
    """섹션 안의 **모든** 코드블록을 순서대로."""
    return re.findall(FENCE, block or "", re.S)


def split_segments(text):
    """산문/코드블록을 **원래 순서대로** [("text",…)|("code",…)] 로."""
    segs = []
    for p in re.split(r"(```[a-z]*\n.*?\n```)", text or "", flags=re.S):
        cb = re.match(FENCE, p, re.S)
        if cb:
            segs.append(("code", cb.group(1)))
        elif p.strip():
            segs.append(("text", p.strip()))
    return segs


def split_options(sel):
    """선택지 섹션 → [{mark, lead, codes[]}]. 펜스를 인식해 항목 경계를 잡는다."""
    opts, cur, buf, in_fence = [], None, [], False

    def flush():
        if cur is not None:
            body = "\n".join(buf)
            cur["codes"] = re.findall(FENCE, body, re.S)
            opts.append(cur)

    for line in (sel or "").split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            buf.append(line)
            continue
        m = None if in_fence else re.match(r"^([①②③④])\s*(.*)$", line.strip())
        if m:
            flush()
            cur, buf = {"mark": m.group(1), "lead": m.group(2).strip()}, []
            continue
        buf.append(line)
    flush()
    return opts


def parse(path):
    t = path.read_text(encoding="utf-8")
    meta = dict(re.findall(r"^(\w+): (.+)$", re.search(r"<!--meta\n(.*?)\n-->", t, re.S).group(1), re.M))
    body = t[t.find("-->") + 3:]
    sec = split_sections(body)
    q = {"n": int(meta["번호"]), "ans": int(meta["정답"])}
    # 발문 — 산문/코드블록을 순서대로 보존(코드블록을 버리지 않는다)
    q["stem_parts"] = split_segments(sec.get("문제", ""))
    # [아 래] — 박스 안의 모든 코드블록
    q["below"] = all_code_blocks(sec.get("[아 래]"))
    # 선택지 — lead 문장 + 딸린 코드블록
    q["opts"] = split_options(sec.get("선택지", ""))
    # 해설
    why_key = next((k for k in sec if k.startswith("왜 ")), None)
    q["why"] = sec.get(why_key, "") if why_key else ""
    q["oab"] = re.findall(r"^\| ([①②③④]) \| (\S+) \| (.+?) \|$", sec.get("오답 이유", ""), re.M)
    key_key = next((k for k in sec if "이 문제의 핵심" in k), None)
    q["key"] = sec.get(key_key, "") if key_key else ""
    m = re.search(r"^📌 한 줄 정리: (.+)$", t, re.M)
    q["oneline"] = m.group(1) if m else ""
    return q


def render_question(q):
    parts = q["stem_parts"]
    head_text = parts[0][1] if parts and parts[0][0] == "text" else ""
    hdr = Table([[num_box(q["n"]), Paragraph(esc(head_text), S["stem"])]], colWidths=[NUMW, CONTENT - NUMW])
    hdr.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (0, 0), 0),
                             ("RIGHTPADDING", (0, 0), (0, 0), 3 * mm), ("LEFTPADDING", (1, 0), (1, 0), 0),
                             ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    flow = [hdr, Spacer(1, 2 * mm)]
    # 발문에 이어지는 코드블록·산문(순서 유지)
    for kind, body in parts[1:] if head_text else parts:
        if kind == "code":
            flow += [code_panel(body), Spacer(1, 2 * mm)]
        else:
            flow += [Paragraph(esc(body), S["stem"]), Spacer(1, 2 * mm)]
    if q["below"]:
        flow += [below_box(q["below"]), Spacer(1, 2 * mm)]
    opt_has_code = False
    for o in q["opts"]:
        flow.append(Paragraph(esc_plain(f"{o['mark']} {o['lead']}".strip()), S["opt"]))  # 보기는 볼드 없이
        if o["codes"]:
            opt_has_code = True
            flow += [Spacer(1, 1 * mm), code_panel(o["codes"], indent=IND + OPT_HANG), Spacer(1, 1.5 * mm)]
    # 선택지에 코드가 붙으면 분량이 커서 통째로 묶으면 페이지가 밀린다 → 자연 분할 허용
    return ([*flow, Spacer(1, 4.5 * mm)] if opt_has_code
            else [KeepTogether(flow), Spacer(1, 4.5 * mm)])


def answer_grid(qs):
    ncol = 5
    rows, row = [], []
    for i, q in enumerate(qs):
        row.append(Paragraph(f"{q['n']}. <b>{'①②③④'[q['ans']-1]}</b>", S["gridcell"]))
        if len(row) == ncol:
            rows.append(row); row = []
    if row:
        row += [Paragraph("", S["gridcell"])] * (ncol - len(row)); rows.append(row)
    t = Table(rows, colWidths=[CONTENT / ncol] * ncol)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
                           ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fafafa")),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    return t


def render_why(why):
    """왜 N인가: 산문 문단 + ```블록은 mono로."""
    flow = []
    parts = re.split(r"(```[a-z]*\n.*?\n```)", why, flags=re.S)
    for p in parts:
        p = p.strip("\n")
        if not p:
            continue
        cb = re.match(r"```[a-z]*\n(.*?)\n```", p, re.S)
        if cb:
            flow.append(Preformatted(realign_box(cb.group(1)), S["mono"], maxLineLength=130))
            flow.append(Spacer(1, 1.5 * mm))
        else:
            for line in p.split("\n"):
                line = line.strip()
                if line and not line.startswith(">"):
                    flow.append(Paragraph(esc(re.sub(r"^[-•]\s*", "", line)), S["why"]))
    return flow


def render_oab(oab, ans):
    head = [Paragraph("선택지", S["cellc"]), Paragraph("판정", S["cellc"]), Paragraph("이유", S["cellc"])]
    data = [head]
    for mark, verdict, reason in oab:
        v = verdict.strip("*").replace("✗", "×")  # ✗ 글리프가 폰트에 없어 ×로 표시
        col = ACCENT if mark == "①②③④"[ans - 1] else DARK
        data.append([Paragraph(f"<font color='{col}'><b>{mark}</b></font>", S["cellc"]),
                     Paragraph(f"<b>{v}</b>" if verdict.startswith("**") else v, S["cellc"]),
                     Paragraph(esc(reason), S["cell"])])
    t = Table(data, colWidths=[12 * mm, 12 * mm, CONTENT - 24 * mm - 6 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d0d0d0")),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0ee")),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return Table([["", t]], colWidths=[6 * mm, CONTENT - 6 * mm],
                 style=[("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0)])


def render_answer(q):
    flow = [Paragraph(f"문제 {q['n']}. &nbsp;정답 <font color='#c0392b'><b>{'①②③④'[q['ans']-1]}</b></font>", S["ans_hd"])]
    flow += render_why(q["why"])
    if q["oab"]:
        flow.append(Spacer(1, 1 * mm))
        flow.append(render_oab(q["oab"], q["ans"]))
    # ✅ 이 문제의 핵심 (섹션이 파일 끝까지라 '📌 한 줄 정리' 줄은 빼고 렌더 — 아래에서 따로 출력)
    key = "\n".join(l for l in q["key"].split("\n") if not l.lstrip().startswith("📌"))
    if key.strip():
        flow.append(Spacer(1, 1.5 * mm))
        flow.append(Paragraph("<b>▪ 이 문제의 핵심</b>", S["ans_hd2"]))
        flow += render_why(key)
    if q["oneline"]:
        flow.append(Spacer(1, 1.2 * mm))
        flow.append(Paragraph(f"<b>▪ 한 줄 정리</b> &nbsp;{esc(q['oneline'])}", S["why"]))
    flow.append(Spacer(1, 2 * mm))
    return flow


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("KR", 8); canvas.setFillColor(GRAY)
    canvas.drawCentredString(A4W / 2, 9 * mm, str(doc.page))
    canvas.restoreState()


def build(round_dir):
    files = sorted((round_dir / "문제").glob("mock-*.md"),
                   key=lambda p: int(re.search(r"mock-(\d+)", p.name).group(1)))
    qs = [parse(f) for f in files]
    story = [Paragraph(f"SQLP 과목 III 튜닝 스타일 모의문제 · {round_dir.name}", S["title"]),
             Spacer(1, 2 * mm),
             Paragraph(f"SQL 자격검정 실전문제 3장 스타일 · 4지선다 · 총 {len(qs)}문항 · 원본 창작", S["intro"]),
             Spacer(1, 1 * mm), HRFlowable(width="100%", thickness=1.0, color=DARK), Spacer(1, 5 * mm)]
    for q in qs:
        story += render_question(q)
    story.append(PageBreak())
    story.append(Paragraph("정답 및 해설", S["anshdr"]))
    story.append(Paragraph("■ 정답 모아보기", S["gridcap"]))
    story.append(answer_grid(qs))
    story.append(Spacer(1, 5 * mm))
    story.append(HRFlowable(width="100%", thickness=0.8, color=GRAY))
    for q in qs:
        story += render_answer(q)
    return story


def main():
    args = [a for a in sys.argv[1:]]
    round_name = args[0] if args else DEFAULT_ROUND
    round_dir = Path(round_name)
    if not round_dir.is_absolute():
        round_dir = ROOT / round_name
    out = Path(args[1]) if len(args) > 1 else round_dir / f"모의고사_{round_dir.name}.pdf"
    register(); styles()
    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=LM, rightMargin=RM,
                            topMargin=16 * mm, bottomMargin=15 * mm,
                            title=f"SQLP 과목 III 모의문제 {round_dir.name}")
    doc.build(build(round_dir), onFirstPage=footer, onLaterPages=footer)
    print(out)


if __name__ == "__main__":
    main()
