# -*- coding: utf-8 -*-
"""
generate_report_pdf.py - 项目报告 PDF 生成器

功能：读取 report/项目报告.md，生成像素风和学术风两种 PDF。
依赖：reportlab（已安装）
"""

import os
import re
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,
    Table, TableStyle, Preformatted, ListFlowable, ListItem, KeepTogether
)


# =====================================================================
# 注册中文字体
# =====================================================================
def register_fonts():
    """注册系统中文字体，失败则使用 reportlab 默认字体。"""
    candidates = [
        ("NotoSansSC", "C:/WINDOWS/Fonts/NotoSansSC-VF.ttf"),
        ("NotoSansSC-Regular", "C:/WINDOWS/Fonts/Noto Sans SC (TrueType).otf"),
        ("STSong", "C:/WINDOWS/Fonts/STSONG.TTF"),
        ("SimSun", "C:/WINDOWS/Fonts/simsun.ttc"),
        ("MicrosoftYaHei", "C:/WINDOWS/Fonts/msyh.ttc"),
    ]
    registered = []
    for name, path in candidates:
        if os.path.exists(path) and name not in registered:
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                registered.append(name)
            except Exception:
                pass
    return registered


REGISTERED_FONTS = register_fonts()
SANS_FONT = REGISTERED_FONTS[0] if REGISTERED_FONTS else "Helvetica"
SERIF_FONT = next((f for f in REGISTERED_FONTS if "Song" in f or "Sun" in f or "Serif" in f), SANS_FONT)


# =====================================================================
# Markdown 简单解析
# =====================================================================
def parse_markdown(md_text):
    """
    将 Markdown 文本解析为结构化段落列表。
    返回：[(type, content, level), ...]
    """
    lines = md_text.splitlines()
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 空行
        if not stripped:
            i += 1
            continue

        # 标题
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            text = stripped[level:].strip()
            blocks.append(("heading", text, level))
            i += 1
            continue

        # 代码块
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            blocks.append(("code", "\n".join(code_lines), lang))
            i += 1
            continue

        # 表格
        if "|" in stripped and i + 1 < len(lines) and "---" in lines[i + 1]:
            table_lines = [stripped]
            i += 1
            while i < len(lines) and "|" in lines[i]:
                table_lines.append(lines[i].strip())
                i += 1
            blocks.append(("table", table_lines, 0))
            continue

        # 普通段落（收集连续非空行）
        para_lines = [line]
        i += 1
        while i < len(lines) and lines[i].strip():
            para_lines.append(lines[i])
            i += 1
        text = " ".join(p.strip() for p in para_lines)
        blocks.append(("paragraph", text, 0))

    return blocks


def escape_xml(text):
    """转义 XML 特殊字符，避免被 reportlab 解析为标签。"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline_markup(text):
    """将 Markdown 行内标记转换为 reportlab 支持的 <font> / <code> 标记。"""
    # 先整体转义，防止原始 <tag> 被解析
    text = escape_xml(text)
    # 加粗 **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # 斜体 *text*
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
    # 行内代码 `text`（已转义的内容重新用 Courier 字体包裹）
    text = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", text)
    return text


def parse_table(table_lines):
    """解析 Markdown 表格为二维列表。"""
    rows = []
    for idx, line in enumerate(table_lines):
        if "---" in line:
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = [c for c in cells if c]
        if cells:
            rows.append(cells)
    return rows


# =====================================================================
# 样式定义
# =====================================================================
def make_pixel_styles():
    """像素风样式：活泼、色块、直角边框。"""
    styles = {
        "title": ParagraphStyle(
            "PixelTitle", fontName=SANS_FONT, fontSize=28, leading=34,
            textColor=colors.HexColor("#E07A5F"), spaceAfter=18,
            alignment=1,  # 居中
        ),
        "subtitle": ParagraphStyle(
            "PixelSubtitle", fontName=SANS_FONT, fontSize=12, leading=16,
            textColor=colors.HexColor("#3D405B"), spaceAfter=24,
            alignment=1,
        ),
        "h1": ParagraphStyle(
            "PixelH1", fontName=SANS_FONT, fontSize=20, leading=26,
            textColor=colors.white, spaceBefore=20, spaceAfter=12,
            backColor=colors.HexColor("#E07A5F"), borderPadding=8,
            borderWidth=3, borderColor=colors.HexColor("#3D405B"),
        ),
        "h2": ParagraphStyle(
            "PixelH2", fontName=SANS_FONT, fontSize=16, leading=22,
            textColor=colors.HexColor("#3D405B"), spaceBefore=16, spaceAfter=8,
            borderWidth=0, borderColor=colors.HexColor("#E07A5F"),
            borderPadding=4, leftIndent=0,
        ),
        "h3": ParagraphStyle(
            "PixelH3", fontName=SANS_FONT, fontSize=13, leading=18,
            textColor=colors.HexColor("#81B29A"), spaceBefore=12, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "PixelBody", fontName=SANS_FONT, fontSize=10.5, leading=16,
            textColor=colors.HexColor("#2D3436"), spaceAfter=8,
            firstLineIndent=0,
        ),
        "code": ParagraphStyle(
            "PixelCode", fontName="Courier", fontSize=8, leading=11,
            textColor=colors.HexColor("#2D3436"), leftIndent=8,
            backColor=colors.HexColor("#F4F1DE"), borderPadding=8,
            borderWidth=2, borderColor=colors.HexColor("#3D405B"),
        ),
        "list": ParagraphStyle(
            "PixelList", fontName=SANS_FONT, fontSize=10.5, leading=16,
            textColor=colors.HexColor("#2D3436"), leftIndent=18, spaceAfter=4,
        ),
    }
    return styles


def make_academic_styles():
    """学术风样式：简洁、正式、适合打印。"""
    styles = {
        "title": ParagraphStyle(
            "AcadTitle", fontName=SERIF_FONT, fontSize=22, leading=28,
            textColor=colors.HexColor("#1a1a1a"), spaceAfter=12,
            alignment=1,
        ),
        "subtitle": ParagraphStyle(
            "AcadSubtitle", fontName=SANS_FONT, fontSize=11, leading=15,
            textColor=colors.HexColor("#444444"), spaceAfter=30,
            alignment=1,
        ),
        "h1": ParagraphStyle(
            "AcadH1", fontName=SERIF_FONT, fontSize=16, leading=22,
            textColor=colors.HexColor("#1a1a1a"), spaceBefore=20, spaceAfter=10,
            borderWidth=1, borderColor=colors.HexColor("#cccccc"),
            borderPadding=6, backColor=colors.HexColor("#f7f7f7"),
        ),
        "h2": ParagraphStyle(
            "AcadH2", fontName=SERIF_FONT, fontSize=14, leading=20,
            textColor=colors.HexColor("#1a1a1a"), spaceBefore=14, spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "AcadH3", fontName=SANS_FONT, fontSize=12, leading=17,
            textColor=colors.HexColor("#333333"), spaceBefore=10, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "AcadBody", fontName=SERIF_FONT, fontSize=11, leading=17,
            textColor=colors.HexColor("#1a1a1a"), spaceAfter=6,
            firstLineIndent=22,
        ),
        "code": ParagraphStyle(
            "AcadCode", fontName="Courier", fontSize=8.5, leading=12,
            textColor=colors.HexColor("#1a1a1a"), leftIndent=10,
            backColor=colors.HexColor("#f5f5f5"), borderPadding=8,
            borderWidth=0.5, borderColor=colors.HexColor("#dddddd"),
        ),
        "list": ParagraphStyle(
            "AcadList", fontName=SERIF_FONT, fontSize=11, leading=17,
            textColor=colors.HexColor("#1a1a1a"), leftIndent=22, spaceAfter=3,
        ),
    }
    return styles


# =====================================================================
# 构建 PDF 内容
# =====================================================================
def build_pdf_elements(blocks, styles, theme="pixel"):
    """根据解析后的 Markdown 块和样式生成 reportlab 元素列表。"""
    elements = []

    for idx, (btype, content, level) in enumerate(blocks):
        if btype == "heading":
            if level == 1:
                # 封面标题特殊处理（第一个 h1 作为文档标题）
                if idx == 0:
                    elements.append(Spacer(1, 3 * cm))
                    elements.append(Paragraph(inline_markup(content), styles["title"]))
                else:
                    elements.append(Paragraph(inline_markup(content), styles["h1"]))
            elif level == 2:
                elements.append(Paragraph(inline_markup(content), styles["h2"]))
            else:
                elements.append(Paragraph(inline_markup(content), styles["h3"]))

        elif btype == "paragraph":
            text = inline_markup(content)
            elements.append(Paragraph(text, styles["body"]))

        elif btype == "code":
            # 代码块使用 Preformatted 保留缩进和换行
            elements.append(Spacer(1, 4))
            elements.append(Preformatted(content, styles["code"]))
            elements.append(Spacer(1, 4))

        elif btype == "table":
            rows = parse_table(content)
            if rows:
                data = [[Paragraph(cell, styles["body"]) for cell in row] for row in rows]
                if theme == "pixel":
                    tstyle = TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E07A5F")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), SANS_FONT),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("GRID", (0, 0), (-1, -1), 2, colors.HexColor("#3D405B")),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFFFFF")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ])
                else:
                    tstyle = TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1a1a1a")),
                        ("FONTNAME", (0, 0), (-1, 0), SERIF_FONT),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ])
                table = Table(data, colWidths=None)
                table.setStyle(tstyle)
                elements.append(Spacer(1, 6))
                elements.append(table)
                elements.append(Spacer(1, 6))

    return elements


# =====================================================================
# 页面模板
# =====================================================================
def add_page_number(canvas, doc, theme):
    """在页脚添加页码。"""
    page_num = canvas.getPageNumber()
    text = f"- {page_num} -"
    if theme == "pixel":
        canvas.setFillColor(colors.HexColor("#3D405B"))
        canvas.setFont(SANS_FONT, 9)
    else:
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.setFont(SANS_FONT, 9)
    canvas.drawCentredString(A4[0] / 2, 1.2 * cm, text)


def create_document(filename, theme):
    """创建基础文档模板。"""
    doc = BaseDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height,
        id="normal"
    )
    template = PageTemplate(
        id="default",
        frames=frame,
        onPage=lambda canvas, doc: add_page_number(canvas, doc, theme),
    )
    doc.addPageTemplates([template])
    return doc


# =====================================================================
# 主流程
# =====================================================================
def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    md_path = os.path.join(base_dir, "项目报告.md")
    if not os.path.exists(md_path):
        print(f"[ERROR] 找不到 {md_path}")
        sys.exit(1)

    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    blocks = parse_markdown(md_text)

    # 像素风
    pixel_doc = create_document(os.path.join(base_dir, "像素风_项目报告.pdf"), "pixel")
    pixel_elements = build_pdf_elements(blocks, make_pixel_styles(), "pixel")
    pixel_doc.build(pixel_elements)
    print("[OK] 像素风项目报告已生成：report/像素风_项目报告.pdf")

    # 学术风
    academic_doc = create_document(os.path.join(base_dir, "学术风格_项目报告.pdf"), "academic")
    academic_elements = build_pdf_elements(blocks, make_academic_styles(), "academic")
    academic_doc.build(academic_elements)
    print("[OK] 学术风格项目报告已生成：report/学术风格_项目报告.pdf")


if __name__ == "__main__":
    main()
