"""rich md(문제/mock-*.md)를 직접 읽어 노랭이 룩 시험지 PDF를 만듭니다.

    python _tools/render.py [출력.pdf]

중간 DSL을 거치지 않고 md를 파싱합니다. 실행계획·TKPROF 표의 ASCII 정렬을
위해 한글이 정확히 2배폭인 고정폭 폰트(굴림체, gulim.ttc subfontIndex=1)를
씁니다. 폰트 경로는 아래 상수로 자족.
"""

import html
import re
import sys
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
문제_DIR = ROOT / "문제"

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


def num_box(n):
    cell = Table([[Paragraph(str(n), S["num"])]], colWidths=[9.5 * mm], rowHeights=[7 * mm])
    cell.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.9, DARK), ("ROUNDEDCORNERS", [3, 3, 3, 3]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return cell


def below_box(code):
    ribbon = Table([[Paragraph("아 래", S["boxtitle"])]], colWidths=[20 * mm], rowHeights=[5.4 * mm])
    ribbon.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), DARK), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    body = Preformatted(code.strip("\n"), S["mono"], maxLineLength=130)
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


def first_code_block(block):
    m = re.search(r"```[a-z]*\n(.*?)\n```", block or "", re.S)
    return m.group(1) if m else None


def parse(path):
    t = path.read_text(encoding="utf-8")
    meta = dict(re.findall(r"^(\w+): (.+)$", re.search(r"<!--meta\n(.*?)\n-->", t, re.S).group(1), re.M))
    body = t[t.find("-->") + 3:]
    sec = split_sections(body)
    q = {"n": int(meta["번호"]), "ans": int(meta["정답"])}
    # 발문(코드블록 제외한 산문)
    q["stem"] = re.sub(r"```.*?```", "", sec.get("문제", ""), flags=re.S).strip()
    # [아 래]
    q["below"] = first_code_block(sec.get("[아 래]"))
    # 선택지
    q["opts"] = re.findall(r"^([①②③④] .+)$", sec.get("선택지", ""), re.M)
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
    hdr = Table([[num_box(q["n"]), Paragraph(esc(q["stem"]), S["stem"])]], colWidths=[NUMW, CONTENT - NUMW])
    hdr.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (0, 0), 0),
                             ("RIGHTPADDING", (0, 0), (0, 0), 3 * mm), ("LEFTPADDING", (1, 0), (1, 0), 0),
                             ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    flow = [hdr, Spacer(1, 2 * mm)]
    if q["below"]:
        flow += [below_box(q["below"]), Spacer(1, 2 * mm)]
    for o in q["opts"]:
        flow.append(Paragraph(esc_plain(o), S["opt"]))  # 보기는 볼드 없이
    return [KeepTogether(flow), Spacer(1, 4.5 * mm)]


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
            flow.append(Preformatted(cb.group(1), S["mono"], maxLineLength=130))
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


def build():
    files = sorted(문제_DIR.glob("mock-*.md"), key=lambda p: int(re.search(r"mock-(\d+)", p.name).group(1)))
    qs = [parse(f) for f in files]
    story = [Paragraph("SQLP 과목 III 튜닝 스타일 모의문제", S["title"]),
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
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "모의고사_20문항.pdf"
    register(); styles()
    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=LM, rightMargin=RM,
                            topMargin=16 * mm, bottomMargin=15 * mm, title="SQLP 과목 III 모의문제")
    doc.build(build(), onFirstPage=footer, onLaterPages=footer)
    print(out)


if __name__ == "__main__":
    main()
