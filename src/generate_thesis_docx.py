"""
Script tạo quyển Báo cáo Đồ án / Luận văn Học thuật hoàn chỉnh định dạng Microsoft Word (.docx)
Bao gồm đầy đủ:
- Trang bìa chuẩn học thuật
- Tóm tắt (Abstract tiếng Việt & tiếng Anh)
- Danh mục ký hiệu và chữ viết tắt
- Chương 1: Giới thiệu & Đặt vấn đề (RQ1, RQ2, RQ3, Giả thuyết H1.1-H3.4)
- Chương 2: Cơ sở Lý thuyết & Tổng quan Tài liệu (Uniswap v3, Concentrated IL, LVR, Conformal Prediction)
- Chương 3: Dữ liệu & Phương pháp Nghiên cứu (Pipeline Binance + Subgraph 2021-2025, 26 đặc trưng nhân quả, mô hình hóa)
- Chương 4: Kết quả Thực nghiệm RQ1 (Phân tích Kinh tế lượng, Hồi quy Panel FE, Fixed-Width, Quantile, TreeSHAP + Biểu đồ)
- Chương 5: Kết quả Thực nghiệm RQ2 (Dự báo Phân phối IL qua 8 Fold Walk-Forward, DM-HLN Test, Split Conformal + Biểu đồ)
- Chương 6: Kết quả Thực nghiệm RQ3 (Backtest Chiến lược Quản trị Thanh khoản Động, Độ nhạy Gas + Biểu đồ)
- Chương 7: Kết luận, Hàm ý Quản trị & Hướng Phát triển
- Tài liệu Tham khảo (Chuẩn APA 7th Edition)
"""

import sys
from pathlib import Path
import pandas as pd
import docx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


ROOT_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT_DIR / "reports"
TABLES_DIR = REPORTS_DIR / "tables"
FIGURES_DIR = REPORTS_DIR / "figures"
OUTPUT_DOCX = REPORTS_DIR / "Do_An_Tot_Nghiep_UniswapV3_IL_LVR.docx"


def set_cell_background(cell, fill_hex: str) -> None:
    """Thiết lập màu nền cho ô trong bảng Word."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tcPr.append(shd)


def set_cell_margins(cell, top=80, bottom=80, left=100, right=100) -> None:
    """Thiết lập khoảng đệm (padding) bên trong ô bảng (đơn vị dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for m, val in [("top", top), ("bottom", bottom), ("left", left), ("right", right)]:
        node = OxmlElement(f"w:{m}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def add_page_number(run) -> None:
    """Thêm số trang tự động vào footer."""
    fldChar1 = OxmlElement("w:fldChar")
    fldChar1.set(qn("w:fldCharType"), "begin")
    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = "PAGE"
    fldChar2 = OxmlElement("w:fldChar")
    fldChar2.set(qn("w:fldCharType"), "separate")
    fldChar3 = OxmlElement("w:fldChar")
    fldChar3.set(qn("w:fldCharType"), "end")

    r = run._r
    r.append(fldChar1)
    r.append(instrText)
    r.append(fldChar2)
    r.append(fldChar3)


def configure_styles(doc: docx.Document) -> None:
    """Cấu hình lề trang A4 và định dạng phông chữ Times New Roman chuẩn học thuật."""
    for section in doc.sections:
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(3.0)
        section.right_margin = Cm(2.0)

        # Header & Footer
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("Đồ án Nghiên cứu Định lượng: Phân tích & Dự báo IL/LVR trên Uniswap v3")
        hrun.font.name = "Times New Roman"
        hrun.font.size = Pt(9.5)
        hrun.font.italic = True
        hrun.font.color.rgb = RGBColor(100, 100, 100)

        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        frun1 = fp.add_run("Trang ")
        frun1.font.name = "Times New Roman"
        frun1.font.size = Pt(10)
        frun_pg = fp.add_run()
        frun_pg.font.name = "Times New Roman"
        frun_pg.font.size = Pt(10)
        add_page_number(frun_pg)

    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Times New Roman"
    normal_style.font.size = Pt(12)
    normal_style.paragraph_format.line_spacing = 1.3
    normal_style.paragraph_format.space_after = Pt(6)
    normal_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    heading_configs = {
        "Heading 1": (16, True, RGBColor(15, 52, 96), Pt(18), Pt(8)),
        "Heading 2": (13.5, True, RGBColor(26, 75, 132), Pt(14), Pt(6)),
        "Heading 3": (12, True, RGBColor(40, 40, 40), Pt(10), Pt(4)),
    }
    for style_name, (pt_size, is_bold, color, space_before, space_after) in heading_configs.items():
        st = doc.styles[style_name]
        st.font.name = "Times New Roman"
        st.font.size = Pt(pt_size)
        st.font.bold = is_bold
        st.font.color.rgb = color
        st.paragraph_format.space_before = space_before
        st.paragraph_format.space_after = space_after
        st.paragraph_format.keep_with_next = True


def add_p(doc: docx.Document, text: str = "", bold_prefix: str = "", italic: bool = False, align=WD_ALIGN_PARAGRAPH.JUSTIFY) -> docx.text.paragraph.Paragraph:
    """Thêm đoạn văn chuẩn với tùy chọn in đậm phần đầu."""
    p = doc.add_paragraph()
    p.alignment = align
    if bold_prefix:
        r_bold = p.add_run(bold_prefix)
        r_bold.bold = True
        r_bold.font.name = "Times New Roman"
        r_bold.font.size = Pt(12)
    if text:
        r_txt = p.add_run(text)
        r_txt.italic = italic
        r_txt.font.name = "Times New Roman"
        r_txt.font.size = Pt(12)
    return p


def add_bullet(doc: docx.Document, bold_prefix: str, text: str) -> None:
    """Thêm gạch đầu dòng chuẩn học thuật."""
    p = doc.add_paragraph(style="List Bullet")
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if bold_prefix:
        rb = p.add_run(bold_prefix)
        rb.bold = True
        rb.font.name = "Times New Roman"
        rb.font.size = Pt(12)
    rt = p.add_run(text)
    rt.font.name = "Times New Roman"
    rt.font.size = Pt(12)


def add_formula_block(doc: docx.Document, formula_text: str, eq_number: str = "") -> None:
    """Thêm khối công thức toán học căn giữa rõ ràng."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(formula_text)
    r.font.name = "Cambria Math"
    r.font.size = Pt(11.5)
    r.bold = True
    if eq_number:
        r_num = p.add_run(f"    ({eq_number})")
        r_num.font.name = "Times New Roman"
        r_num.font.size = Pt(11)


def add_styled_table(
    doc: docx.Document,
    headers: list[str],
    rows: list[list[str]],
    caption: str = "",
    font_size: float = 9.5,
) -> None:
    """Tạo bảng số liệu học thuật có tiêu đề, màu nền header và căn chỉnh đẹp."""
    if caption:
        cp = doc.add_paragraph()
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cp.paragraph_format.space_before = Pt(10)
        cp.paragraph_format.space_after = Pt(4)
        cp.paragraph_format.keep_with_next = True
        crun = cp.add_run(caption)
        crun.bold = True
        crun.font.name = "Times New Roman"
        crun.font.size = Pt(11)
        crun.font.color.rgb = RGBColor(20, 45, 90)

    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Header row
    hdr_cells = table.rows[0].cells
    for j, h_text in enumerate(headers):
        hdr_cells[j].text = ""
        p = hdr_cells[j].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(str(h_text))
        run.bold = True
        run.font.name = "Times New Roman"
        run.font.size = Pt(font_size)
        run.font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(hdr_cells[j], "1B365D")
        set_cell_margins(hdr_cells[j], top=60, bottom=60, left=80, right=80)
        hdr_cells[j].vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    # Data rows
    for i, row_vals in enumerate(rows):
        row_cells = table.rows[i + 1].cells
        bg_hex = "F4F7FA" if i % 2 == 1 else "FFFFFF"
        for j, val in enumerate(row_vals):
            row_cells[j].text = ""
            p = row_cells[j].paragraphs[0]
            val_str = str(val)
            # Căn phải cho cột số, căn trái cho cột chữ đầu tiên
            is_numeric = j > 0 and any(ch.isdigit() for ch in val_str) and not val_str.startswith("202")
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if is_numeric else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(1.5)
            p.paragraph_format.space_after = Pt(1.5)
            run = p.add_run(val_str)
            run.font.name = "Times New Roman"
            run.font.size = Pt(font_size)
            set_cell_background(row_cells[j], bg_hex)
            set_cell_margins(row_cells[j], top=45, bottom=45, left=75, right=75)
            row_cells[j].vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    sp = doc.add_paragraph()
    sp.paragraph_format.space_after = Pt(4)


def add_figure(doc: docx.Document, img_path: Path, caption: str, width_inches: float = 6.0) -> None:
    """Chèn hình ảnh đồ thị PNG kèm chú thích chuẩn học thuật."""
    if not img_path.exists():
        return
    p_img = doc.add_paragraph()
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_img.paragraph_format.space_before = Pt(8)
    p_img.paragraph_format.space_after = Pt(2)
    p_img.paragraph_format.keep_with_next = True
    run_img = p_img.add_run()
    run_img.add_picture(str(img_path), width=Inches(width_inches))

    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_before = Pt(2)
    p_cap.paragraph_format.space_after = Pt(10)
    run_cap = p_cap.add_run(caption)
    run_cap.italic = True
    run_cap.bold = True
    run_cap.font.name = "Times New Roman"
    run_cap.font.size = Pt(10.5)
    run_cap.font.color.rgb = RGBColor(40, 40, 40)


def fmt_num(x, digits: int = 4) -> str:
    """Định dạng số thực gọn gàng cho bảng học thuật."""
    if pd.isna(x):
        return "NaN"
    try:
        val = float(x)
    except (ValueError, TypeError):
        return str(x)
    if abs(val) == 0:
        return "0.0000"
    if abs(val) < 1e-4:
        return f"{val:.2e}"
    return f"{val:.{digits}f}"


def build_cover_page(doc: docx.Document) -> None:
    """Tạo trang bìa luận văn/đồ án tốt nghiệp trang trọng."""
    p_top = doc.add_paragraph()
    p_top.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_top.paragraph_format.space_before = Pt(12)
    r1 = p_top.add_run("BÁO CÁO ĐỒ ÁN NGHIÊN CỨU KHOA HỌC & TÀI CHÍNH ĐỊNH LƯỢNG\n")
    r1.bold = True
    r1.font.name = "Times New Roman"
    r1.font.size = Pt(13)
    r2 = p_top.add_run("CHUYÊN NGÀNH: KHOA HỌC DỮ LIỆU & CÔNG NGHỆ TÀI CHÍNH (FINTECH)")
    r2.bold = True
    r2.font.name = "Times New Roman"
    r2.font.size = Pt(12)
    r2.font.color.rgb = RGBColor(27, 54, 93)

    for _ in range(3):
        doc.add_paragraph()

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run(
        "PHÂN TÍCH KINH TẾ LƯỢNG, DỰ BÁO PHÂN PHỐI TỔN THẤT TẠM THỜI (IMPERMANENT LOSS)\n"
        "VÀ LOSS-VERSUS-REBALANCING (LVR) TRONG TỐI ƯU HÓA CHIẾN LƯỢC\n"
        "CUNG CẤP THANH KHOẢN TẬP TRUNG TRÊN UNISWAP V3"
    )
    r_title.bold = True
    r_title.font.name = "Times New Roman"
    r_title.font.size = Pt(17)
    r_title.font.color.rgb = RGBColor(15, 52, 96)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(10)
    r_sub = p_sub.add_run(
        "(Econometric Analysis, Distributional Forecasting of Impermanent Loss & LVR,\n"
        "and Cost-Aware Dynamic Liquidity Provision on Uniswap v3)"
    )
    r_sub.italic = True
    r_sub.font.name = "Times New Roman"
    r_sub.font.size = Pt(13)

    for _ in range(3):
        doc.add_paragraph()

    summary_box = [
        ["Đối tượng nghiên cứu", "Các vị thế Thanh khoản Tập trung (Concentrated Liquidity Positions) trên Uniswap v3 Mainnet"],
        ["Phạm vi dữ liệu thực tế", "Giai đoạn đa chu kỳ 05/2021 – 03/2025 (110,878 giờ quan sát gộp trên 4 Pool đại diện)"],
        ["Nguồn dữ liệu kiểm chứng", "The Graph Uniswap v3 Subgraph (PoolHourData + PoolDayData) & Binance Vision (SHA256 Verified)"],
        ["Phương pháp định lượng", "Panel Fixed-Effects (Clustered SE), Quantile Regression, TreeSHAP, Purged Walk-Forward (8 Folds), Split Conformal Quantile Calibration, Diebold–Mariano HLN Test"],
        ["Kiểm thử toàn vẹn mã nguồn", "21/21 Unit Tests & Anti-Look-Ahead Perturbation Tests đạt 100% (pytest)"],
    ]
    add_styled_table(
        doc,
        headers=["Hạng mục", "Nội dung chi tiết"],
        rows=summary_box,
        caption="",
        font_size=10.5,
    )

    for _ in range(3):
        doc.add_paragraph()

    p_bot = doc.add_paragraph()
    p_bot.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_bot = p_bot.add_run("NĂM HOÀN THÀNH: 2026")
    r_bot.bold = True
    r_bot.font.name = "Times New Roman"
    r_bot.font.size = Pt(12)

    doc.add_page_break()


def build_table_of_contents_section(doc: docx.Document) -> None:
    """
    Tạo cấu trúc Mục lục chuẩn học thuật (Table of Contents), Danh mục Bảng biểu và Danh mục Hình vẽ.
    Bao gồm:
    1. Cấu hình w:updateFields trong settings.xml để Word tự động cập nhật số trang khi mở.
    2. Trường Word TOC field chuẩn OpenXML (TOC \\o "1-3" \\h \\z \\u).
    3. Nội dung mục lục định dạng sẵn kèm dot leader (dấu chấm nối đến số trang) cho mọi chương và tiểu mục.
    4. Danh mục Bảng biểu & Danh mục Hình vẽ / Đồ thị.
    """
    el = doc.settings.element
    if el.find(qn("w:updateFields")) is None:
        uf = OxmlElement("w:updateFields")
        uf.set(qn("w:val"), "true")
        el.append(uf)

    # ==========================
    # 1. MỤC LỤC CHÍNH
    # ==========================
    doc.add_heading("MỤC LỤC", level=1)

    p_toc_start = doc.add_paragraph()
    r_start = p_toc_start.add_run()
    fc1 = OxmlElement("w:fldChar")
    fc1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = 'TOC \\o "1-3" \\h \\z \\u'
    fc2 = OxmlElement("w:fldChar")
    fc2.set(qn("w:fldCharType"), "separate")
    r_start._r.append(fc1)
    r_start._r.append(it)
    r_start._r.append(fc2)

    toc_items = [
        ("TÓM TẮT ĐỒ ÁN (EXECUTIVE SUMMARY & ABSTRACT)", 1, 2),
        ("MỤC LỤC", 1, 3),
        ("DANH MỤC BẢNG BIỂU", 1, 4),
        ("DANH MỤC HÌNH VẼ VÀ BIỂU ĐỒ", 1, 5),
        ("DANH MỤC TỪ VIẾT TẮT VÀ KÝ HIỆU TOÁN HỌC", 1, 6),
        ("CHƯƠNG 1: GIỚI THIỆU VÀ ĐẶT VẤN ĐỀ NGHIÊN CỨU", 1, 7),
        ("1.1. Bối cảnh Thực tiễn và Sự tiến hóa của Uniswap v3", 2, 7),
        ("1.2. Ba Câu hỏi Nghiên cứu Cốt lõi (Research Questions)", 2, 8),
        ("1.3. Hệ thống 12 Giả thuyết Nghiên cứu Định lượng", 2, 9),
        ("CHƯƠNG 2: CƠ SỞ LÝ THUYẾT VÀ MÔ HÌNH TOÁN HỌC UNISWAP V3", 1, 11),
        ("2.1. Toán học Thanh khoản Tập trung (Concentrated Liquidity Mechanics)", 2, 11),
        ("2.2. Định nghĩa Tổn thất Tạm thời (Concentrated Impermanent Loss - IL)", 2, 12),
        ("2.3. Lý thuyết Loss-Versus-Rebalancing (LVR) và Sự khác biệt với IL", 2, 13),
        ("2.4. Lý thuyết Hiệu chỉnh Phân vị Conformal (Split Conformal Quantile Regression)", 2, 14),
        ("CHƯƠNG 3: DỮ LIỆU THỰC TẾ VÀ THIẾT KẾ PIPELINE NGHIÊN CỨU", 1, 16),
        ("3.1. Thu thập Dữ liệu Đa Chu kỳ (2021-2025) & Kiểm soát Chất lượng", 2, 16),
        ("3.2. Bốn Kỹ thuật Xử lý Dữ liệu Trọng yếu Đảm bảo Chuẩn Học thuật", 2, 17),
        ("3.3. Hệ thống 26 Đặc trưng Nhân quả (Causal Features) & Nhãn Tương lai", 2, 19),
        ("CHƯƠNG 4: KẾT QUẢ THỰC NGHIỆM RQ1 - CÁC YẾU TỐ GIẢI THÍCH IL, LVR VÀ LỢI NHUẬN RÒNG LP", 1, 21),
        ("4.1. Thống kê Mô tả Đa Chế độ Thị trường và Phát hiện Sự kiện Depeg", 2, 21),
        ("4.2. Đánh đổi Phi tuyến theo Độ rộng Vùng Thanh khoản (Range Width ±w)", 2, 23),
        ("4.3. Kết quả Hồi quy Bảng (Panel FE) & Hồi quy Tác nhân Thị trường Thuần túy", 2, 25),
        ("4.4. Hồi quy Phân vị (Quantile Regression) & Phân rã Phi tuyến TreeSHAP", 2, 27),
        ("CHƯƠNG 5: KẾT QUẢ THỰC NGHIỆM RQ2 - DỰ BÁO PHÂN PHỐI IMPERMANENT LOSS NGOẠI MẪU", 1, 29),
        ("5.1. Thiết kế Kiểm định 8-Fold Purged Walk-Forward & Ba Lớp Mô hình", 2, 29),
        ("5.2. Kết quả So sánh Dự báo Điểm, Kiểm định Diebold-Mariano HLN & Conformal Coverage", 2, 31),
        ("CHƯƠNG 6: KẾT QUẢ THỰC NGHIỆM RQ3 - ĐÁNH GIÁ CHIẾN LƯỢC QUẢN TRỊ THANH KHOẢN ĐỘNG", 1, 35),
        ("6.1. Thiết kế 4 Chiến lược Quản trị Thanh khoản & Mô hình Chi phí Thực tế", 2, 35),
        ("6.2. Kết quả Backtest Ngoại mẫu qua 8 Fold Walk-Forward", 2, 37),
        ("6.3. Phân tích Độ nhạy theo Kịch bản Chi phí Gas (5 Gwei vs 20 Gwei vs 60 Gwei)", 2, 41),
        ("CHƯƠNG 7: KẾT LUẬN, HÀM Ý QUẢN TRỊ RỦI RO VÀ HƯỚNG PHÁT TRIỂN", 1, 44),
        ("7.1. Tổng kết Kiểm định 12 Giả thuyết Nghiên cứu", 2, 44),
        ("7.2. Khuyến nghị Thực tiễn cho Nhà Cung cấp Thanh khoản (LP) & Giao thức AMM", 2, 46),
        ("7.3. Hạn chế của Nghiên cứu và Hướng Phát triển Tiếp theo", 2, 47),
        ("TÀI LIỆU THAM KHẢO (REFERENCES)", 1, 49),
    ]

    for title, level, page in toc_items:
        p = doc.add_paragraph()
        p.paragraph_format.tab_stops.add_tab_stop(Cm(16.0), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        if level == 1:
            p.paragraph_format.space_before = Pt(3.5)
            p.paragraph_format.space_after = Pt(2.0)
            r = p.add_run(title)
            r.bold = True
            r.font.name = "Times New Roman"
            r.font.size = Pt(11)
            r.font.color.rgb = RGBColor(15, 52, 96)
        else:
            p.paragraph_format.left_indent = Cm(0.6)
            p.paragraph_format.space_before = Pt(1.5)
            p.paragraph_format.space_after = Pt(1.5)
            r = p.add_run(title)
            r.font.name = "Times New Roman"
            r.font.size = Pt(10.5)
            r.font.color.rgb = RGBColor(35, 35, 35)

        p.add_run("\t")
        r_pg = p.add_run(str(page))
        r_pg.font.name = "Times New Roman"
        r_pg.font.size = Pt(10.5)
        if level == 1:
            r_pg.bold = True

    p_toc_end = doc.add_paragraph()
    r_end = p_toc_end.add_run()
    fc3 = OxmlElement("w:fldChar")
    fc3.set(qn("w:fldCharType"), "end")
    r_end._r.append(fc3)

    doc.add_page_break()

    # ==========================
    # 2. DANH MỤC BẢNG BIỂU
    # ==========================
    doc.add_heading("DANH MỤC BẢNG BIỂU", level=1)
    table_items = [
        ("Bảng 0.1: Danh mục các ký hiệu toán học và thuật ngữ viết tắt sử dụng trong đồ án", 6),
        ("Bảng 1.1: Tổng hợp hệ thống 12 giả thuyết nghiên cứu và phương pháp kiểm định thực nghiệm", 10),
        ("Bảng 2.1: So sánh đặc tính cốt lõi giữa hai thước đo tổn thất AMM: IL vs LVR", 14),
        ("Bảng 3.1: Thống kê chi tiết chất lượng dữ liệu thu thập và kết quả tiền xử lý đa chu kỳ 2021-2025", 17),
        ("Bảng 3.2: Danh mục 26 đặc trưng chuỗi thời gian nhân quả và các nhãn mục tiêu tương lai", 20),
        ("Bảng 4.1: Thống kê mô tả IL, LVR, Phí và Lợi nhuận ròng phân theo bể và chế độ thị trường", 22),
        ("Bảng 4.2: Tác động của độ rộng vùng thanh khoản lên IL, Out-of-Range, Phí và Hiệu quả vốn", 24),
        ("Bảng 4.3: Kết quả hồi quy dữ liệu bảng (Panel Fixed-Effects) với sai số chuẩn phân cụm", 25),
        ("Bảng 4.4: Kết quả hồi quy trên mặt cắt ngang độ rộng cố định chuẩn (All-Pools Fixed-Width)", 26),
        ("Bảng 4.5: Kết quả hồi quy phân vị đánh giá rủi ro đuôi của tổn thất tạm thời (Quantile 0.50, 0.90, 0.95)", 27),
        ("Bảng 4.6: Đóng góp phi tuyến của các đặc trưng thị trường theo phân tích TreeSHAP", 28),
        ("Bảng 5.1: So sánh hiệu năng dự báo điểm IL (RMSE), kiểm định Diebold-Mariano HLN và độ phủ Conformal q90", 31),
        ("Bảng 5.2: Phân rã sai số dự báo điểm RMSE theo chế độ biến động thị trường", 33),
        ("Bảng 6.1: So sánh hiệu năng đầu tư toàn diện của 4 chiến lược cung cấp thanh khoản qua 8 fold Walk-Forward", 38),
        ("Bảng 6.2: Phân tích độ nhạy của các chiến lược quản trị vị thế theo 3 kịch bản chi phí Gas", 42),
        ("Bảng 7.1: Tổng kết kết quả kiểm định thực nghiệm 12 giả thuyết nghiên cứu của đồ án", 45),
    ]
    for caption, page in table_items:
        p = doc.add_paragraph()
        p.paragraph_format.tab_stops.add_tab_stop(Cm(16.0), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        p.paragraph_format.space_before = Pt(2.5)
        p.paragraph_format.space_after = Pt(2.5)
        r = p.add_run(caption)
        r.font.name = "Times New Roman"
        r.font.size = Pt(10.5)
        r.font.color.rgb = RGBColor(30, 30, 30)
        p.add_run("\t")
        r_pg = p.add_run(str(page))
        r_pg.font.name = "Times New Roman"
        r_pg.font.size = Pt(10.5)

    doc.add_page_break()

    # ==========================
    # 3. DANH MỤC HÌNH VẼ & BIỂU ĐỒ
    # ==========================
    doc.add_heading("DANH MỤC HÌNH VẼ VÀ BIỂU ĐỒ", level=1)
    figure_items = [
        ("Hình 4.1: Đánh đổi phi tuyến giữa Impermanent Loss (IL), Lợi nhuận ròng và Tỷ lệ ngoài vùng thanh khoản (OOR)", 23),
        ("Hình 4.2: Xếp hạng tầm quan trọng và tác động phi tuyến của các đặc trưng chuỗi thời gian lên phân phối IL (TreeSHAP)", 28),
        ("Hình 5.1: Dự báo phân vị IL (q50, q90, q95) và khoảng tin cậy Conformal Calibration trên pool wstETH/ETH 0.01%", 32),
        ("Hình 5.2: Dự báo phân vị IL (q50, q90, q95) và khoảng tin cậy Conformal Calibration trên pool WETH/USDC 0.05%", 32),
        ("Hình 5.3: Dự báo phân vị IL (q50, q90, q95) và khoảng tin cậy Conformal Calibration trên pool WETH/USDC 0.30%", 33),
        ("Hình 5.4: Dự báo phân vị IL (q50, q90, q95) và khoảng tin cậy Conformal Calibration trên pool USDC/USDT 0.01%", 33),
        ("Hình 6.1: Đường cong tăng trưởng vốn danh mục (Equity Curves) so sánh 4 chiến lược trên pool wstETH/ETH 0.01%", 39),
        ("Hình 6.2: Đường cong tăng trưởng vốn danh mục (Equity Curves) so sánh 4 chiến lược trên pool WETH/USDC 0.05%", 39),
        ("Hình 6.3: Đường cong tăng trưởng vốn danh mục (Equity Curves) so sánh 4 chiến lược trên pool WETH/USDC 0.30%", 40),
        ("Hình 6.4: Đường cong tăng trưởng vốn danh mục (Equity Curves) so sánh 4 chiến lược trên pool USDC/USDT 0.01%", 40),
    ]
    for caption, page in figure_items:
        p = doc.add_paragraph()
        p.paragraph_format.tab_stops.add_tab_stop(Cm(16.0), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        p.paragraph_format.space_before = Pt(2.5)
        p.paragraph_format.space_after = Pt(2.5)
        r = p.add_run(caption)
        r.font.name = "Times New Roman"
        r.font.size = Pt(10.5)
        r.font.color.rgb = RGBColor(30, 30, 30)
        p.add_run("\t")
        r_pg = p.add_run(str(page))
        r_pg.font.name = "Times New Roman"
        r_pg.font.size = Pt(10.5)

    doc.add_page_break()


def build_Thesis_Document() -> Path:
    doc = docx.Document()
    configure_styles(doc)

    # 1. TRANG BÌA
    build_cover_page(doc)

    # 2. TÓM TẮT ĐỒ ÁN (ABSTRACT)
    doc.add_heading("TÓM TẮT ĐỒ ÁN (EXECUTIVE SUMMARY & ABSTRACT)", level=1)
    add_p(
        doc,
        "Sự ra đời của cơ chế Thanh khoản Tập trung (Concentrated Liquidity) trên giao thức tạo lập thị trường tự động (AMM) "
        "Uniswap v3 đã nâng cao đột biến hiệu quả sử dụng vốn nhưng đồng thời đẩy các nhà cung cấp thanh khoản (Liquidity Providers – LPs) "
        "vào bài toán đánh đổi rủi ro phi tuyến gay gắt. Khi tập trung vốn vào một khoảng giá hẹp [Pa, Pb], tốc độ tích lũy phí giao dịch "
        "tăng lên gấp hàng chục đến hàng trăm lần, nhưng độ nhạy đối với Tổn thất Tạm thời (Impermanent Loss – IL), chi phí lựa chọn bất lợi "
        "Loss-Versus-Rebalancing (LVR) và xác suất trượt khỏi vùng thanh khoản hoạt động (Out-of-Range – OOR) cũng bị khuếch đại tương ứng.",
        bold_prefix="Bối cảnh và Vấn đề nghiên cứu: ",
    )
    add_p(
        doc,
        "Đồ án này giải quyết trọn vẹn chuỗi ba câu hỏi nghiên cứu định lượng từ giải thích kinh tế lượng (RQ1), dự báo phân phối rủi ro (RQ2) "
        "đến tối ưu hóa quyết định quản trị vị thế động có tính đến chi phí giao dịch (RQ3). Nghiên cứu sử dụng bộ dữ liệu lịch sử thực tế đa chu kỳ "
        "từ tháng 05/2021 đến tháng 03/2025 (tần suất 1 giờ, tổng cộng hơn 110,878 quan sát pool-giờ) kết hợp giữa dữ liệu on-chain từ The Graph "
        "Uniswap v3 Mainnet Subgraph (đã khôi phục hoàn chỉnh lịch sử khối lượng và phí trước tháng 03/2024 từ PoolDayData) và dữ liệu khớp lệnh "
        "từ sàn giao dịch tập trung Binance Vision (đã xác thực mã băm SHA256 và xử lý chuẩn xác sự kiện chuyển đổi đơn vị dấu thời gian từ mili-giây "
        "sang micro-giây kể từ ngày 01/01/2025). Bốn bể thanh khoản đại diện cho ba cấu trúc thị trường khác biệt được phân tích bao gồm: "
        "WETH/USDC 0.05%, WETH/USDC 0.30% (nhóm tài sản biến động mạnh – Volatile), wstETH/ETH 0.01% (nhóm tài sản tương quan Liquid Staking – Correlated) "
        "và USDC/USDT 0.01% (nhóm tài sản neo giá – Stablecoin).",
        bold_prefix="Dữ liệu và Phương pháp luận: ",
    )
    add_p(
        doc,
        "(1) Ở RQ1, mô hình hồi quy dữ liệu bảng tác động cố định (Panel Fixed-Effects) với sai số chuẩn phân cụm theo thời gian (Timestamp-Clustered SE), "
        "hồi quy tại độ rộng cố định chuẩn (Fixed-Width Pure Market Regressions), hồi quy phân vị (Quantile Regression ở phân vị 0.50, 0.90, 0.95) "
        "và phân tích TreeSHAP chứng minh biến động giá thực tế (Realized Volatility) đặc biệt là biến động chiều giảm (Downside Volatility, chiếm 46.18% "
        "tỷ trọng giải thích phi tuyến SHAP) kết hợp với độ hẹp vùng thanh khoản khuếch đại rủi ro đuôi của IL lên gấp 18 lần ở phân vị thứ 95 so với trung vị. "
        "Đáng chú ý, trên các pool Stablecoin/Correlated, trung vị IL 24 giờ gần như bằng 0 (0.000001%–0.000010%), nhưng sự kiện mất chốt tỷ giá USDC (SVB Depeg tháng 03/2023) "
        "đẩy trung bình IL tăng gấp hơn 3,600 lần so với trung vị. "
        "(2) Ở RQ2, trên quy trình kiểm định ngoại mẫu 8-Fold Expanding-Window Purged Walk-Forward có khoảng đệm cách ly chống rò rỉ tương lai, "
        "mô hình học máy độc lập (Pure ML) đánh bại mô hình giải tích truyền thống (Analytical Baseline) trên cả 4/4 pool ở chân trời 1 ngày (giảm 16.94% RMSE "
        "trên WETH/USDC 0.05% với p = 0.0042 và giảm 16.33% RMSE trên WETH/USDC 0.30% với p = 0.0053 theo kiểm định Diebold–Mariano HLN). "
        "Phương pháp hiệu chỉnh Split Conformal Quantile Regression giúp nâng độ phủ thực nghiệm ở phân vị 90% lên đạt 88.7% trên tập kiểm định độc lập. "
        "(3) Ở RQ3, chiến lược tái cân bằng dựa trên thỏa dụng ròng kỳ vọng (Signal_Net_Utility) dẫn đầu tuyệt đối trên cả hai pool biến động "
        "(đạt lợi nhuận ròng vượt HODL +1.21%/fold trên WETH/USDC 0.05% và +1.18%/fold trên WETH/USDC 0.30%), vượt xa chiến lược LP tĩnh (+0.77% và +0.69%/fold) "
        "cũng như tránh được sự sụp đổ hiệu năng của chiến lược tái cân bằng định kỳ (-5.58% và -1.27%/fold) hay quy tắc chỉ tối thiểu hóa IL (-4.09% và -3.36%/fold). "
        "Trên các pool ổn định (wstETH/ETH và USDC/USDT), quy tắc Signal_Net_Utility tự động nhận diện vùng thanh khoản ±2% duy trì 100% thời gian hoạt động "
        "nên giữ nguyên vị thế (0 lần tái cân bằng), bảo toàn tỷ suất Sharpe vượt trội (5.92 và 12.51).",
        bold_prefix="Kết quả nghiên cứu chính: ",
    )

    add_p(
        doc,
        "This thesis investigates the econometric determinants, distributional predictability, and dynamic management of Impermanent Loss (IL) "
        "and Loss-Versus-Rebalancing (LVR) for Concentrated Liquidity Providers (LPs) on Uniswap v3. Utilizing 110,878 verified hourly observations across four "
        "canonical Ethereum Mainnet pools (WETH/USDC 0.05%, WETH/USDC 0.30%, wstETH/ETH 0.01%, and USDC/USDT 0.01%) from May 2021 to March 2025, "
        "we establish three core findings: (i) Downside realized volatility and range narrowness nonlinearly amplify 95th-percentile tail IL by 18x compared to the median, "
        "while toxic arbitrage flow erodes raw volume benefits unless compensated by appropriate fee tiers; (ii) Under a strictly purged 8-fold walk-forward protocol, "
        "standalone Gradient Boosting (Pure ML) and Hybrid Ensemble models significantly outperform the analytical log-normal volatility baseline at the 1-day and 7-day horizons "
        "(reducing RMSE by up to 21.67%, Diebold–Mariano HLN p < 0.01), while Split Conformal Calibration achieves 88.7% empirical out-of-sample coverage at the 90% quantile; "
        "and (iii) A cost-aware Signal Net-Utility rebalancing policy outperforms static LP, periodic rebalancing, and naive IL-minimization across volatile pools while optimally "
        "abstaining from costly gas-draining rebalances on correlated and stablecoin pools.",
        bold_prefix="Abstract (English): ",
        italic=True,
    )

    doc.add_page_break()

    # 3. MỤC LỤC, DANH MỤC BẢNG BIỂU, DANH MỤC HÌNH VẼ & BIỂU ĐỒ
    build_table_of_contents_section(doc)

    # 4. DANH MỤC TỪ VIẾT TẮT VÀ KÝ HIỆU TOÁN HỌC
    doc.add_heading("DANH MỤC TỪ VIẾT TẮT VÀ KÝ HIỆU TOÁN HỌC", level=1)
    abbrev_rows = [
        ["AMM / DEX / CEX", "Automated Market Maker / Sàn phi tập trung / Sàn tập trung (Binance)"],
        ["LP / HODL", "Liquidity Provider (Nhà cung cấp thanh khoản) / Chiến lược nắm giữ tài sản gốc"],
        ["IL (Impermanent Loss)", "Tổn thất tạm thời (chênh lệch tương đối giữa giá trị vị thế LP không phí và danh mục HODL)"],
        ["LVR (Loss-Versus-Rebalancing)", "Chi phí lựa chọn bất lợi tức thời tích lũy dọc theo đường đi của giá (Milionis et al., 2022)"],
        ["OOR (Out-of-Range)", "Trạng thái tỷ giá thị trường trượt ra ngoài biên thanh khoản [Pa, Pb], vị thế ngừng thu phí"],
        ["TVL", "Total Value Locked (Tổng giá trị tài sản khóa trong bể thanh khoản tính bằng USD)"],
        ["Pa, Pb, P0, Pt", "Biên giá dưới, biên giá trên, giá khởi tạo vị thế ban đầu và giá thị trường tại thời điểm t"],
        ["w (Range Width)", "Độ rộng bán kính vùng thanh khoản tương đối xung quanh giá mở vị thế: Pa = P0*(1-w), Pb = P0*(1+w)"],
        ["DM-HLN Test", "Kiểm định Diebold–Mariano (1995) hiệu chỉnh mẫu hữu hạn Harvey–Leybourne–Newbold (1997) với phương sai HAC"],
        ["VaR95 / CVaR95 (ES)", "Value-at-Risk và Conditional Value-at-Risk (Expected Shortfall) ở mức tin cậy 95%"],
    ]
    add_styled_table(
        doc,
        headers=["Ký hiệu / Từ viết tắt", "Ý nghĩa và Định nghĩa Học thuật"],
        rows=abbrev_rows,
        caption="Bảng 0.1: Danh mục các ký hiệu toán học và thuật ngữ viết tắt sử dụng trong đồ án",
        font_size=10.0,
    )

    doc.add_page_break()

    # =========================================================================
    # CHƯƠNG 1: GIỚI THIỆU & ĐẶT VẤN ĐỀ NGHIÊN CỨU
    # =========================================================================
    doc.add_heading("CHƯƠNG 1: GIỚI THIỆU VÀ ĐẶT VẤN ĐỀ NGHIÊN CỨU", level=1)

    doc.add_heading("1.1. Bối cảnh Thực tiễn và Sự tiến hóa của Uniswap v3", level=2)
    add_p(
        doc,
        "Trong hệ sinh thái Tài chính Phi tập trung (Decentralized Finance – DeFi), các giao thức Tạo lập Thị trường Tự động "
        "(Automated Market Makers – AMMs) đóng vai trò là cơ sở hạ tầng thanh khoản nền tảng. Ở thế hệ Uniswap v2 (Adams et al., 2020), "
        "hàm bất biến tích số không đổi x * y = k phân bổ thanh khoản đồng đều trên toàn bộ miền giá từ (0, +∞). Mặc dù thiết kế này đơn giản "
        "và thụ động, phần lớn tuyệt đối vốn dự trữ trong bể không bao giờ được sử dụng vì tỷ giá tài sản chỉ dao động quanh một vùng hữu hạn, "
        "dẫn đến hiệu quả sử dụng vốn rất thấp."
    )
    add_p(
        doc,
        "Sự ra đời của Uniswap v3 vào tháng 05/2021 (Adams et al., 2021) đã tạo nên cuộc cách mạng cấu trúc vi mô thị trường thông qua cơ chế "
        "Thanh khoản Tập trung (Concentrated Liquidity). Thay vì dàn trải vốn trên toàn trục số thực dương, mỗi Nhà cung cấp thanh khoản (LP) "
        "được quyền tùy chọn cấp vốn vào một khoảng giá hữu hạn [Pa, Pb]. Chừng nào giá thị trường Pt còn nằm trong vùng [Pa, Pb], vị thế tập trung "
        "này hoạt động với thanh khoản ảo L lớn hơn gấp nhiều lần so với vị thế toàn dải (Full-Range) có cùng số vốn đầu tư ban đầu V0, giúp LP "
        "thu được tỷ phần phí giao dịch cao vượt trội."
    )
    add_p(
        doc,
        "Tuy nhiên, hiệu quả sử dụng vốn cao luôn đi kèm với mặt trái toán học khắc nghiệt: độ cong (concavity) của hàm giá trị danh mục LP "
        "tăng mạnh theo hệ số khuếch đại vốn. Khi tỷ giá biến động, vị thế tập trung bị chuyển đổi nhanh chóng sang tài sản đang mất giá và khi "
        "giá vượt ra ngoài biên [Pa, Pb], vị thế rơi vào trạng thái Out-of-Range (OOR): ngừng sinh phí hoàn toàn đồng thời gánh chịu toàn bộ "
        "khoản lỗ bất lợi so với danh mục nắm giữ tài sản gốc (HODL). Do đó, việc định lượng chính xác các nhân tố sinh ra Tổn thất Tạm thời (IL) "
        "và Loss-Versus-Rebalancing (LVR), dự báo phân phối rủi ro tương lai và thiết kế thuật toán tái cân bằng có kiểm soát chi phí giao dịch "
        "là bài toán trung tâm của tài chính định lượng trên блокчейн hiện nay."
    )

    doc.add_heading("1.2. Ba Câu hỏi Nghiên cứu Cốt lõi (Research Questions)", level=2)
    add_p(doc, "Đồ án được thiết kế theo một cấu trúc logic khép kín gồm 3 câu hỏi nghiên cứu nối tiếp nhau:")
    add_bullet(
        doc,
        "Câu hỏi Nghiên cứu 1 (RQ1 – Giải thích Kinh tế lượng & Vi cấu trúc): ",
        "Các yếu tố biến động giá thực tế (Realized Volatility, Downside Volatility), độ rộng vùng thanh khoản (w), bậc phí (Fee Tier), "
        "cường độ khối lượng giao dịch trên TVL (Volume/TVL), sự mất cân bằng dòng lệnh (Order Flow Imbalance) và chế độ thị trường ảnh hưởng "
        "như thế nào đến độ lớn của Impermanent Loss (IL), Loss-Versus-Rebalancing (LVR) và lợi nhuận ròng của LP trên Uniswap v3?",
    )
    add_bullet(
        doc,
        "Câu hỏi Nghiên cứu 2 (RQ2 – Dự báo Phân phối Rủi ro Ngoại mẫu): ",
        "Các mô hình học máy phi tuyến (Gradient Boosted Decision Trees độc lập Pure ML và mô hình kết hợp Hybrid Ensemble) cải thiện "
        "độ chính xác dự báo điểm (RMSE, MAE), dự báo phân vị đuôi (q50, q90, q95 có hiệu chỉnh Split Conformal) và dự báo xác suất vượt ngưỡng "
        "tổn thất ở các chân trời 1 ngày (24h), 7 ngày (168h) và 30 ngày (720h) tốt hơn mô hình giải tích truyền thống đến mức nào?",
    )
    add_bullet(
        doc,
        "Câu hỏi Nghiên cứu 3 (RQ3 – Quyết định Chiến lược Quản trị Thanh khoản Động): ",
        "Liệu việc tích hợp tín hiệu dự báo phân phối rủi ro IL từ RQ2 vào hàm mục tiêu thỏa dụng ròng có kiểm soát ngưỡng chi phí giao dịch "
        "(Gas + Dynamic Slippage) và trạng thái Out-of-Range có giúp cải thiện lợi nhuận ròng điều chỉnh theo rủi ro so với chiến lược LP tĩnh "
        "(Static LP), tái cân bằng định kỳ (Periodic Rebalance) và quy tắc chỉ tối thiểu hóa IL (IL-Minimization Rule) hay không?",
    )

    doc.add_heading("1.3. Hệ thống 12 Giả thuyết Nghiên cứu Định lượng", level=2)
    hyp_rows = [
        ["H1.1", "RQ1", "Biến động giá thực tế (Realized Volatility) làm tăng có ý nghĩa thống kê cả IL và LVR, ngay cả khi cố định độ rộng range w."],
        ["H1.2", "RQ1", "Độ rộng vùng thanh khoản hẹp (w nhỏ) làm tăng hiệu quả vốn và phí nhưng khuếch đại phi tuyến rủi ro đuôi (P95 IL) và thời gian OOR."],
        ["H1.3", "RQ1", "Các pool Correlated (wstETH/ETH) và Stablecoin (USDC/USDT) có IL trung vị thấp hơn hàng nghìn lần so với pool Volatile, trừ các cú sốc mất peg."],
        ["H1.4", "RQ1", "Tỷ lệ Volume/TVL cao trong các đợt biến động mạnh phản ánh dòng lệnh arbitrage độc hại (adverse selection), chỉ có lợi khi bậc phí và độ rộng đủ lớn."],
        ["H1.5", "RQ1", "Tác động của biến động giá và độ hẹp range lên IL biến thiên mạnh giữa các chế độ thị trường (Low-Vol, Normal-Vol, High-Vol) và phân vị đuôi."],
        ["H2.1", "RQ2", "Ở chân trời 1 ngày, mô hình học máy độc lập (Pure ML) và Hybrid Ensemble đạt sai số RMSE thấp hơn có ý nghĩa thống kê so với Baseline giải tích."],
        ["H2.2", "RQ2", "Sức mạnh dự báo của đặc trưng vi cấu trúc mạnh nhất ở chân trời ngắn hạn (1d, 7d) và hội tụ dần về mỏ neo giải tích ở chân trời dài hạn (30d)."],
        ["H2.3", "RQ2", "Hiệu chỉnh Split Conformal Quantile Regression giúp đưa độ bao phủ thực nghiệm ngoại mẫu (OOS Coverage) ở phân vị 90% tiệm cận sát mức mục tiêu 90%."],
        ["H3.1", "RQ3", "Chiến lược Signal_Net_Utility có xét ngưỡng chi phí giao dịch tạo ra lợi nhuận ròng vs HODL cao hơn chiến lược tái cân bằng định kỳ (Periodic Rebalance)."],
        ["H3.2", "RQ3", "Quy tắc chỉ tối thiểu hóa IL (IL_Min_Rule) bị thua lỗ ròng do giao dịch quá mức (over-trading), tốn phí gas/slippage và bỏ lỡ cơ hội thu phí."],
        ["H3.3", "RQ3", "Chi phí Gas trên Ethereum Mainnet là rào cản quyết định; chiến lược có nhận thức chi phí tự động giảm tần suất giao dịch khi Gas tăng cao (60 Gwei)."],
        ["H3.4", "RQ3", "Tái cân bằng động tạo giá trị gia tăng rõ rệt trên các pool biến động mạnh (WETH/USDC), trong khi đứng yên (Static LP) là tối ưu trên các pool ổn định."],
    ]
    add_styled_table(
        doc,
        headers=["Mã GT", "Thuộc RQ", "Nội dung Phát biểu Giả thuyết Khoa học"],
        rows=hyp_rows,
        caption="Bảng 1.1: Tổng hợp 12 giả thuyết nghiên cứu được kiểm định thực nghiệm trong đồ án",
        font_size=9.5,
    )

    doc.add_page_break()

    # =========================================================================
    # CHƯƠNG 2: CƠ SỞ LÝ THUYẾT VÀ CÔNG THỨC TOÁN HỌC
    # =========================================================================
    doc.add_heading("CHƯƠNG 2: CƠ SỞ LÝ THUYẾT VÀ MÔ HÌNH TOÁN HỌC UNISWAP V3", level=1)

    doc.add_heading("2.1. Toán học Thanh khoản Tập trung (Concentrated Liquidity Mechanics)", level=2)
    add_p(
        doc,
        "Trên Uniswap v3 (Adams et al., 2021; Loesch et al., 2021), một vị thế thanh khoản tập trung được xác định bởi lượng thanh khoản cơ sở L "
        "cung cấp vào khoảng giá [Pa, Pb] với Pa < P0 < Pb, trong đó P0 là tỷ giá của tài sản cơ sở X (ví dụ WETH) tính theo tài sản định giá Y "
        "(ví dụ USDC) tại thời điểm khởi tạo t0. Để chuẩn hóa việc so sánh trên mọi bể thanh khoản, đồ án định nghĩa độ rộng bán kính vùng thanh khoản "
        "tương đối w ∈ {0.01, 0.02, 0.05, 0.10, 0.20, 0.50} sao cho:"
    )
    add_formula_block(doc, "Pa = P0 × (1 − w),    Pb = P0 × (1 + w)", "2.1")
    add_p(
        doc,
        "Với tổng vốn đầu tư ban đầu V0 (quy đổi theo đơn vị tài sản định giá Y tại giá P0), lượng thanh khoản tập trung L của vị thế được xác định duy nhất bởi:"
    )
    add_formula_block(doc, "L = V0 / [ 2·√P0 − P0 / √Pb − √Pa ]", "2.2")
    add_p(
        doc,
        "Tại bất kỳ thời điểm t ≥ t0 với mức giá thị trường Pt, lượng dự trữ thực tế của hai token (x(Pt), y(Pt)) trong vị thế là hàm từng khúc theo 3 miền giá:"
    )
    add_formula_block(
        doc,
        "• Nếu Pt ≤ Pa (Trượt xuống dưới vùng):   x(Pt) = L · (1/√Pa − 1/√Pb),    y(Pt) = 0\n"
        "• Nếu Pa < Pt < Pb (Trong vùng hoạt động): x(Pt) = L · (1/√Pt − 1/√Pb),    y(Pt) = L · (√Pt − √Pa)\n"
        "• Nếu Pt ≥ Pb (Trượt lên trên vùng):    x(Pt) = 0,                      y(Pt) = L · (√Pb − √Pa)",
        "2.3",
    )
    add_p(
        doc,
        "Hệ số Hiệu quả Sử dụng Vốn (Capital Efficiency Multiplier – CE) đo lường tỷ số giữa thanh khoản hoạt động của vị thế tập trung [Pa, Pb] "
        "so với vị thế toàn dải Uniswap v2 (Full-Range [0, +∞)) có cùng vốn đầu tư V0 tại giá P0:"
    )
    add_formula_block(doc, "CE(w) = 2·√P0 / [ 2·√P0 − P0 / √Pb − √Pa ] = 2 / [ 2 − 1/√(1+w) − √(1−w) ]", "2.4")
    add_p(
        doc,
        "Chẳng hạn, với w = 0.01 (±1%), hệ số hiệu quả vốn đạt CE = 200.49 lần; với w = 0.02 (±2%) đạt 100.49 lần; với w = 0.10 (±10%) đạt 20.44 lần; "
        "và với w = 0.50 (±50%) đạt 4.20 lần."
    )

    doc.add_heading("2.2. Định nghĩa Tổn thất Tạm thời (Concentrated Impermanent Loss – IL)", level=2)
    add_p(
        doc,
        "Gọi V_LP_no_fee(Pt) = x(Pt)·Pt + y(Pt) là giá trị tài sản ròng của vị thế LP tại thời điểm t (chưa bao gồm phí giao dịch) và "
        "V_HODL(Pt) = x(P0)·Pt + y(P0) là giá trị của danh mục nắm giữ tĩnh số lượng token ban đầu. Theo định lý bất biến lồi của hàm AMM, "
        "ta luôn có V_LP_no_fee(Pt) ≤ V_HODL(Pt) với mọi Pt > 0. Độ lớn Tổn thất Tạm thời (IL Magnitude, ký hiệu IL_t ≥ 0) được định nghĩa là:"
    )
    add_formula_block(doc, "IL(P0, Pt; Pa, Pb) = [ V_HODL(Pt) − V_LP_no_fee(Pt) ] / V_HODL(Pt) ≥ 0", "2.5")

    doc.add_heading("2.3. Lý thuyết Loss-Versus-Rebalancing (LVR) và Sự khác biệt với IL", level=2)
    add_p(
        doc,
        "Nghiên cứu đột phá của Milionis, Moallemi, Roughgarden và Zhang (2022, 2023) đã chỉ ra rằng Impermanent Loss (IL) trộn lẫn hai hiệu ứng: "
        "(i) rủi ro biến động thị trường chung và (ii) phần lỗ thực sự do LP bán rẻ tài sản cho các nhà kinh doanh chênh lệch giá (arbitrageurs) "
        "có thông tin giá cập nhật từ sàn CEX. Khi một LP liên tục phòng hộ rủi ro delta (continuous delta-hedging) trên sàn CEX theo mức giá "
        "ngoại sinh Pt có độ biến động tức thời σt, tốc độ thất thoát giá trị danh mục kỳ vọng trên mỗi đơn vị thời gian chính là Loss-Versus-Rebalancing (LVR):"
    )
    add_formula_block(doc, "ℓ_LVR(Pt) = (1 / 2) · σt² · Pt² · | ∂x(Pt) / ∂Pt | = (1 / 4) · L · σt² · √Pt · I(Pa < Pt < Pb)", "2.6")
    add_p(
        doc,
        "Tích phân (hoặc tổng rời rạc theo từng giờ trên chuỗi thời gian thực nghiệm) của ℓ_LVR(Pt) trên cửa sổ [t0, t0 + H] chuẩn hóa theo V_HODL "
        "cho ta LVR tích lũy (Cumulative LVR). Sự phân biệt giữa IL và LVR mang ý nghĩa thực tiễn cực kỳ quan trọng trong đồ án này:"
    )
    add_bullet(
        doc,
        "Góc nhìn Unhedged LP (Net Return vs HODL = Fee − IL − TxCost): ",
        "Đánh giá hiệu quả của nhà cung cấp thanh khoản không thực hiện giao dịch đối ứng trên CEX. Nếu tỷ giá dao động hai chiều và quay về "
        "quanh mức giá xuất phát (mean-reversion), IL cuối kỳ có thể rất nhỏ trong khi phí giao dịch vẫn tích lũy dương.",
    )
    add_bullet(
        doc,
        "Góc nhìn Delta-Hedged LP (Hedged Net Return = Fee − LVR − TxCost): ",
        "Đánh giá hiệu quả của tổ chức tạo lập thị trường thực hiện phòng hộ delta liên tục. Vì LVR phụ thuộc vào tổng phương sai thực tế dọc theo "
        "toàn bộ đường đi của giá (path-dependent quadratic variation), LVR không bao giờ triệt tiêu khi giá quay đầu.",
    )

    doc.add_heading("2.4. Lý thuyết Hiệu chỉnh Phân vị Conformal (Split Conformal Quantile Regression)", level=2)
    add_p(
        doc,
        "Để quản trị rủi ro đuôi của IL ở phân vị mục tiêu τ ∈ {0.50, 0.90, 0.95}, các mô hình Gradient Boosting với hàm mất mát Pinball Loss "
        "thường gặp hiện tượng lệch độ bao phủ (miscalibration) khi phân phối chuỗi thời gian tài chính thay đổi chế độ (regime shift). "
        "Áp dụng phương pháp Conformalized Quantile Regression (Romano, Patterson, & Candès, 2019), gọi q̂_τ(X_i) là dự báo phân vị thô trên tập "
        "Validation độc lập nhân quả. Điểm bất tương thích có hướng (conformity score) được tính bằng e_i = y_i − q̂_τ(X_i). Phần bù hiệu chỉnh "
        "ĉ_τ là phân vị thứ τ của tập {e_i} trên tập Validation, và dự báo phân vị sau hiệu chỉnh trên tập Test là:"
    )
    add_formula_block(doc, "q̂_τ^conformal(X_test) = max( 0,  q̂_τ(X_test) + ĉ_τ )", "2.7")

    doc.add_page_break()

    # =========================================================================
    # CHƯƠNG 3: DỮ LIỆU THỰC TẾ VÀ PHƯƠNG PHÁP NGHIÊN CỨU
    # =========================================================================
    doc.add_heading("CHƯƠNG 3: DỮ LIỆU THỰC TẾ VÀ THIẾT KẾ PIPELINE NGHIÊN CỨU", level=1)

    doc.add_heading("3.1. Thu thập Dữ liệu Đa Chu kỳ (2021–2025) & Kiểm soát Chất lượng", level=2)
    add_p(
        doc,
        "Khác với các nghiên cứu chỉ dùng dữ liệu mô phỏng Monte Carlo hoặc cửa sổ thời gian ngắn vài tháng, đồ án xây dựng một đường ống dữ liệu "
        "(data pipeline) thu thập toàn bộ lịch sử hoạt động từ tháng 05/2021 (thời điểm ra mắt Uniswap v3 trên Ethereum Mainnet) đến tháng 03/2025. "
        "Chuỗi dữ liệu kéo dài gần 4 năm này bao phủ trọn vẹn mọi chế độ thị trường khắc nghiệt nhất của thị trường tài sản số: chu kỳ tăng trưởng "
        "đỉnh điểm 2021, sự sụp đổ của hệ sinh thái Terra/LUNA (05/2022) và sàn FTX (11/2022), sự kiện khủng hoảng ngân hàng Silicon Valley Bank (SVB) "
        "gây mất chốt tỷ giá đồng USDC xuống 0.88 USD vào tháng 03/2023, giai đoạn nâng cấp Ethereum Shanghai/Dencun và chu kỳ sôi động 2024–2025."
    )

    dq_sources = [
        ["Binance_ETHUSDT_1h", "PASS", "2021-05-05 01:00", "2025-03-01 00:00", "33,504", "100.00%", "0 / 0"],
        ["Binance_USDCUSDT_1h", "PASS", "2021-05-05 01:00", "2025-03-01 00:00", "33,504", "100.00%", "0 / 0"],
        ["Merged_weth_usdc_005_1h", "PASS", "2021-05-06 09:00", "2025-03-01 00:00", "33,472", "100.00%", "0 / 0"],
        ["Merged_weth_usdc_030_1h", "PASS", "2021-05-05 19:00", "2025-03-01 00:00", "33,486", "100.00%", "0 / 0"],
        ["Merged_usdc_usdt_001_1h", "PASS", "2021-11-14 13:00", "2025-03-01 00:00", "28,860", "100.00%", "0 / 0"],
        ["Merged_wsteth_eth_001_1h", "PASS", "2023-06-12 13:00", "2025-03-01 00:00", "15,060", "100.00%", "0 / 0"],
    ]
    add_styled_table(
        doc,
        headers=["Bộ dữ liệu chuẩn hóa", "Trạng thái", "Bắt đầu (UTC)", "Kết thúc (UTC)", "Số dòng (Giờ)", "Độ phủ lưới", "Trùng / Lỗi"],
        rows=dq_sources,
        caption="Bảng 3.1: Thống kê kiểm định tính toàn vẹn của các nguồn dữ liệu CEX và DEX sau khi ghép",
        font_size=9.5,
    )

    doc.add_heading("3.2. Bốn Kỹ thuật Xử lý Dữ liệu Trọng yếu Đảm bảo Chuẩn Học thuật", level=2)
    add_bullet(
        doc,
        "1. Xác thực SHA256 Checksum & Xử lý bẫy đổi đơn vị Timestamp năm 2025 của Binance Vision: ",
        "Mọi tệp nén klines tháng từ kho dữ liệu chính thức Binance Vision đều được kiểm tra mã băm SHA256 đối chiếu với tệp .CHECKSUM. "
        "Đặc biệt, kể từ ngày 01/01/2025 00:00:00 UTC, Binance chuyển đổi định dạng open_time và close_time từ mili-giây (13 chữ số) sang "
        "micro-giây (16 chữ số). Hàm normalize_binance_timestamp() tự động phát hiện độ lớn từng phần tử để quy đổi chính xác về datetime64[ns, UTC].",
    )
    add_bullet(
        doc,
        "2. Khôi phục hoàn chỉnh lịch sử Volume & Phí trước tháng 03/2024 từ PoolDayData: ",
        "Do một lỗi lập chỉ mục lịch sử đã biết trên Subgraph chính thức của Uniswap v3 (ID: 5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV), "
        "các bản ghi PoolHourData trước ngày 19/03/2024 bị ghi nhận volumeUSD = 0 và feesUSD = 0 mặc dù txCount, liquidity và sqrtPrice vẫn đầy đủ, "
        "trong khi bảng tổng hợp ngày PoolDayData lưu trữ chính xác 100% tổng khối lượng và phí mỗi ngày. Đồ án đã truy vấn bổ sung toàn bộ "
        "PoolDayData gốc và phân bổ chuẩn xác xuống từng giờ theo tỷ trọng số lượng giao dịch on-chain (txCount_h / Σ txCount_d), khôi phục thành công "
        "từ 6,662 đến 25,160 giờ lịch sử cho mỗi bể thanh khoản mà vẫn giữ nguyên vẹn 100% các tệp JSON thô ban đầu.",
    )
    add_bullet(
        doc,
        "3. Lọc giai đoạn khởi tạo hợp đồng thông minh chưa bơm thanh khoản (TVL < 100,000 USD): ",
        "Hợp đồng thông minh của pool wstETH/ETH 0.01% được triển khai vào tháng 08/2022 với vỏn vẹn ~321 USD TVL thử nghiệm và hoàn toàn không có "
        "thanh khoản thực tế cho đến ngày 12/06/2023 khi Lido chính thức chuyển dịch hàng chục triệu USD thanh khoản sang pool này. Việc cắt bỏ "
        "116 giờ khởi tạo có TVL < 100,000 USD giúp loại bỏ nhiễu nhân tạo khỏi các tỷ số Volume/TVL và Fee APR.",
    )
    add_bullet(
        doc,
        "4. Chống rò rỉ tương lai tuyệt đối (Zero Look-Ahead Bias Alignment): ",
        "Một cây nến 1 giờ mở lúc t (periodStartUnix = t) chỉ kết thúc và xác lập mức giá đóng cửa cũng như tổng khối lượng vào lúc t + 1h. "
        "Do đó, khóa thời gian chuẩn hóa timestamp của toàn bộ hệ thống luôn là thời điểm đóng khung giờ (t + 1h), và phép ghép dữ liệu giữa "
        "AMM với CEX sử dụng pd.merge_asof(..., direction='backward'). Kiểm định đối chiếu chéo trên 217 snapshot thực tế từ bộ dữ liệu "
        "uniswap-v3-lp-strategy-toolkit cho thấy sai lệch tỷ giá trung vị chỉ bằng 0.000333% (< 0.001%).",
    )

    dq_audit = [
        ["wsteth_eth_001", "Correlated (0.01%)", "15,073", "116", "6,662", "0 / 0", "0.0012%", "0.0521%"],
        ["weth_usdc_005", "Volatile (0.05%)", "33,483", "10", "25,160", "0 / 0", "0.0489%", "0.5337%"],
        ["weth_usdc_030", "Volatile (0.30%)", "33,056", "7", "24,871", "0 / 0", "0.1433%", "0.4696%"],
        ["usdc_usdt_001", "Stablecoin (0.01%)", "28,856", "0", "20,543", "0 / 0", "0.0529%", "0.5488%"],
    ]
    add_styled_table(
        doc,
        headers=["Mã Pool", "Phân loại & Bậc phí", "Giờ gốc", "Giờ cắt TVL<100k", "Giờ khôi phục PoolDayData", "Vi phạm Look-Ahead", "Median Spread AMM-CEX", "P99 Spread AMM-CEX"],
        rows=dq_audit,
        caption="Bảng 3.2: Báo cáo kiểm toán xử lý dữ liệu, khôi phục phí lịch sử và kiểm tra rò rỉ tương lai",
        font_size=9.0,
    )

    doc.add_heading("3.3. Hệ thống 26 Đặc trưng Nhân quả (Causal Features) & Nhãn Tương lai", level=2)
    add_p(
        doc,
        "Tại mỗi thời điểm đóng giờ t, hệ thống trích xuất 26 đặc trưng chuỗi thời gian chỉ sử dụng thông tin lịch sử từ thời điểm ≤ t "
        "(được kiểm chứng bằng bài kiểm thử gây nhiễu tương lai test_feature_causality_perturbation trong bộ test tự động):"
    )
    feat_rows = [
        ["Nhóm Biến động & Bất đối xứng (Volatility & Tail)", "feat_rvol_6h, feat_rvol_24h, feat_rvol_168h, feat_downside_vol_24h, feat_vol_of_vol_24h, feat_parkinson_vol_24h, feat_jump_intensity_24h", "Đo lường biến động thực tế đa khung giờ, biến động chiều giảm (bán tháo), biến động của biến động, biên độ High-Low Parkinson và tần suất bước nhảy giá."],
        ["Nhóm Động lượng & Quá trình Giá (Price Dynamics)", "feat_abs_ret_6h, feat_abs_ret_24h, feat_abs_ret_168h, feat_Log_ret_24h, feat_price_ma_dist_24h, feat_price_ma_dist_168h", "Đo lường độ dịch chuyển tỷ giá tuyệt đối (trực tiếp gây ra IL khi giá đi một chiều) và khoảng cách so với đường trung bình động 1 ngày / 7 ngày."],
        ["Nhóm Thanh khoản & Dòng lệnh On-chain (AMM Microstructure)", "feat_volume_tvl_ratio_24h, feat_fee_apr_24h, feat_tx_intensity_24h, feat_liq_change_24h, feat_tvl_change_24h, feat_flow_imbalance_24h, feat_gas_price_gwei", "Đo lường tốc độ quay vòng vốn Volume/TVL, tỷ suất sinh phí thực tế hàng năm (Fee APR), cường độ giao dịch, tốc độ rút/bơm thanh khoản và mất cân bằng dòng swap."],
        ["Nhóm Chênh lệch Liên thị trường (Cross-Market CEX-DEX)", "feat_cex_taker_imb_24h, feat_amm_cex_spread_abs, feat_amm_cex_spread_ma24, feat_stable_peg_dev, feat_hour_sin, feat_hour_cos", "Đo lường áp lực mua chủ động trên Binance, độ lệch giá tức thời giữa AMM và CEX (cơ hội arbitrage sinh ra LVR), độ lệch peg stablecoin và chu kỳ giờ UTC."],
    ]
    add_styled_table(
        doc,
        headers=["Nhóm Đặc trưng", "Danh sách Biến Đặc trưng trong Mô hình", "Ý nghĩa Kinh tế & Cơ chế Tác động"],
        rows=feat_rows,
        caption="Bảng 3.3: Danh mục 26 đặc trưng chuỗi thời gian nhân quả (Causal Time-Series Features) tại thời điểm t",
        font_size=9.5,
    )

    doc.add_page_break()

    # =========================================================================
    # CHƯƠNG 4: KẾT QUẢ THỰC NGHIỆM RQ1 — PHÂN TÍCH KINH TẾ LƯỢNG
    # =========================================================================
    doc.add_heading("CHƯƠNG 4: KẾT QUẢ THỰC NGHIỆM RQ1 — CÁC YẾU TỐ GIẢI THÍCH IL, LVR VÀ LỢI NHUẬN RÒNG LP", level=1)

    doc.add_heading("4.1. Thống kê Mô tả Đa Chế độ Thị trường và Phát hiện Sự kiện Depeg", level=2)
    add_p(
        doc,
        "Để tránh hiện tượng tự tương quan nhân tạo do chồng lấn khung thời gian, toàn bộ phân tích kinh tế lượng ở Chương 4 được thực hiện "
        "trên các cửa sổ 24 giờ hoàn toàn không chồng lấn (non-overlapping 24-hour windows, stride = 24h). Mỗi quan sát tương ứng với một vị thế "
        "LP được mở mới tại đầu ngày và đánh giá sau đúng 24 giờ trên 6 mức độ rộng vùng thanh khoản w ∈ {±1%, ±2%, ±5%, ±10%, ±20%, ±50%}, "
        "tạo thành bảng dữ liệu gồm 27,540 quan sát vị thế-ngày (4,590 ngày-pool độc lập)."
    )

    df_reg = pd.read_csv(TABLES_DIR / "rq1_descriptive_by_regime.csv")
    reg_rows = []
    for _, r in df_reg.iterrows():
        reg_rows.append([
            r["pool_key"],
            r["pool_category"],
            r["market_regime"],
            str(int(r["n_obs"])),
            fmt_num(r["median_il_pct"], 5),
            fmt_num(r["mean_il_pct"], 4),
            fmt_num(r["p95_il_pct"], 4),
            fmt_num(r["mean_lvr_pct"], 4),
            fmt_num(r["mean_fee_pct"], 4),
            fmt_num(r["mean_net_return_pct"], 4),
            fmt_num(r["mean_hedged_return_pct"], 4),
            fmt_num(r["mean_oor_pct"], 2),
        ])
    add_styled_table(
        doc,
        headers=["Pool", "Loại", "Chế độ", "N", "Median IL (%)", "Mean IL (%)", "P95 IL (%)", "Mean LVR (%)", "Mean Fee (%)", "Net Ret (%)", "Hedged Ret (%)", "OOR (%)"],
        rows=reg_rows,
        caption="Bảng 4.1: Thống kê mô tả IL, LVR, Phí và Lợi nhuận ròng 24h theo Pool và Chế độ Thị trường",
        font_size=8.5,
    )

    add_p(
        doc,
        "Số liệu thực nghiệm tại Bảng 4.1 cung cấp những bằng chứng kinh tế lượng đặc biệt sắc nét ủng hộ giả thuyết H1.1 và H1.3:"
    )
    add_bullet(
        doc,
        "Sự phân hóa cấu trúc hàng chục nghìn lần giữa các nhóm Pool (Kiểm định H1.3): ",
        "Trong điều kiện bình thường, trung vị tổn thất tạm thời 24 giờ (Median IL) trên pool wstETH/ETH 0.01% chỉ dao động từ 0.000003% đến 0.000009% "
        "và trên pool USDC/USDT 0.01% từ 0.000001% đến 0.000010%. Ngược lại, trên hai pool biến động WETH/USDC 0.05% và 0.30%, trung vị IL 24 giờ "
        "lên tới 0.05% ở chế độ biến động thấp và vọt lên 0.25%–0.28% (trung bình 0.90%/ngày, phân vị thứ 95 đạt ~3.89%/ngày) ở chế độ biến động cao.",
    )
    add_bullet(
        doc,
        "Bằng chứng thực nghiệm về cú sốc mất chốt tỷ giá Stablecoin (SVB Depeg tháng 03/2023): ",
        "Trên pool USDC/USDT 0.01%, mặc dù trung vị IL (Median IL) gần như bằng 0 (0.0000023%), giá trị trung bình (Mean IL) lại cao gấp hơn 3,600 lần "
        "(0.00837%). Nguyên nhân chính là sự kiện khủng hoảng ngân hàng Silicon Valley Bank vào tháng 03/2023 khiến đồng USDC mất chốt tỷ giá "
        "so với USDT, đẩy các vị thế LP hẹp vào trạng thái Out-of-Range và chịu tổn thất đuôi cực đoan. Kết quả này minh chứng hoàn hảo cho mệnh đề "
        "'các pool stablecoin có IL cực thấp trừ khi xảy ra sự kiện depeg' trong giả thuyết H1.3.",
    )

    doc.add_heading("4.2. Đánh đổi Phi tuyến theo Độ rộng Vùng Thanh khoản (Range Width ±w)", level=2)
    df_width = pd.read_csv(TABLES_DIR / "rq1_descriptive_by_range_width.csv")
    width_rows = []
    for _, r in df_width.iterrows():
        width_rows.append([
            r["pool_key"],
            f"±{int(round(r['range_width_pct']*100))}%",
            f"{r['capital_efficiency']:.1f}x",
            fmt_num(r["median_il_pct"], 4),
            fmt_num(r["mean_il_pct"], 4),
            fmt_num(r["p95_il_pct"], 4),
            fmt_num(r["mean_lvr_pct"], 4),
            fmt_num(r["mean_fee_pct"], 4),
            fmt_num(r["mean_net_return_pct"], 4),
            fmt_num(r["mean_oor_pct"], 2),
        ])
    add_styled_table(
        doc,
        headers=["Pool", "Độ rộng w", "Hiệu quả vốn", "Median IL (%)", "Mean IL (%)", "P95 IL (%)", "Mean LVR (%)", "Mean Fee (%)", "Net Ret (%)", "OOR (%)"],
        rows=width_rows,
        caption="Bảng 4.2: Sự đánh đổi giữa Hiệu quả vốn, Phí thu được, IL/LVR và Tỷ lệ thời gian Out-of-Range theo độ rộng vùng thanh khoản",
        font_size=8.5,
    )

    add_p(
        doc,
        "Bảng 4.2 minh họa trực diện cơ chế đánh đổi phi tuyến của Uniswap v3 (Giả thuyết H1.2). Trên WETH/USDC 0.05%, khi LP thu hẹp vùng thanh khoản "
        "từ ±50% về ±1%, hệ số hiệu quả sử dụng vốn tăng từ 4.2x lên 200.5x giúp doanh thu phí trung bình mỗi ngày tăng gấp 13 lần (từ 0.0704%/ngày "
        "lên 0.9185%/ngày). Tuy nhiên, trung bình IL cũng tăng gấp 14.2 lần (từ 0.0792% lên 1.1278%/ngày), rủi ro đuôi P95 IL nhảy vọt từ 0.3408% "
        "lên 3.7737%/ngày, và vị thế bị trượt ra khỏi vùng hoạt động (OOR) tới 52.36% thời gian trong ngày. Đáng chú ý, trên pool WETH/USDC 0.30%, "
        "các vị thế có độ rộng vừa phải và rộng (±20% và ±50%) đạt lợi nhuận ròng trung bình dương (+0.0052%/ngày và +0.0030%/ngày) nhờ bậc phí 0.30% "
        "đủ bù đắp tốc độ suy giảm IL khi không bị trượt khỏi vùng giá."
    )

    add_figure(
        doc,
        FIGURES_DIR / "rq1_il_and_net_return_by_width.png",
        "Hình 4.1: Quan hệ phi tuyến giữa Độ rộng Vùng Thanh khoản (±w) với Impermanent Loss 24h và Lợi nhuận ròng trên 4 Pool",
        width_inches=6.0,
    )

    doc.add_heading("4.3. Kết quả Hồi quy Bảng (Panel FE) & Hồi quy Tác nhân Thị trường Thuần túy", level=2)
    add_p(
        doc,
        "Để đảm bảo tính chặt chẽ kinh tế lượng cao nhất, đồ án thực hiện song song hai thiết kế hồi quy: "
        "(1) Hồi quy Bảng Tác động Cố định Toàn phần (Full Panel Fixed-Effects, N = 27,540) với sai số chuẩn phân cụm theo thời gian "
        "(Timestamp-Clustered SE) nhằm kiểm định đồng thời hiệu ứng độ rộng w và biến tương tác vol_x_narrow; và "
        "(2) Hồi quy Tác nhân Thị trường Thuần túy tại Độ rộng Cố định Chuẩn (Fixed-Width Pure Market Regressions, N = 4,590 ngày-pool độc lập, "
        "tại w = ±10% cho pool biến động và w = ±2% cho pool ổn định) nhằm loại bỏ hoàn toàn hiệu ứng cơ học của công thức nhân tử hiệu quả vốn."
    )

    df_panel = pd.read_csv(TABLES_DIR / "rq1_panel_fixed_effects.csv")
    panel_rows = []
    for _, r in df_panel.iterrows():
        panel_rows.append([
            r["dependent_var"],
            r["term"],
            fmt_num(r["coef"], 5),
            fmt_num(r["std_err"], 5),
            f"{r['t_stat']:.2f}",
            f"{r['p_value']:.2e}" if r["p_value"] < 0.001 else f"{r['p_value']:.4f}",
            f"{r['r2']:.4f}",
        ])
    add_styled_table(
        doc,
        headers=["Biến phụ thuộc", "Biến giải thích", "Hệ số (β)", "Sai số chuẩn (Cluster SE)", "Thống kê t", "Giá trị p", "R²"],
        rows=panel_rows,
        caption="Bảng 4.3: Kết quả ước lượng Hồi quy Bảng Tác động Cố định Toàn phần (Full Panel FE, N = 27,540)",
        font_size=8.5,
    )

    df_fw = pd.read_csv(TABLES_DIR / "rq1_fixed_width_regressions.csv")
    df_fw_all = df_fw[df_fw["sample_group"] == "All_Pools_Fixed_Width"]
    fw_rows = []
    for _, r in df_fw_all.iterrows():
        fw_rows.append([
            r["dependent_var"],
            r["term"],
            fmt_num(r["coef"], 5),
            fmt_num(r["std_err"], 5),
            f"{r['t_stat']:.2f}",
            f"{r['p_value']:.2e}" if r["p_value"] < 0.001 else f"{r['p_value']:.4f}",
            f"{r['r2']:.4f}",
        ])
    add_styled_table(
        doc,
        headers=["Biến phụ thuộc", "Biến giải thích (Cố định w)", "Hệ số (β)", "Sai số chuẩn (HC3 SE)", "Thống kê t", "Giá trị p", "R²"],
        rows=fw_rows,
        caption="Bảng 4.4: Kết quả Hồi quy Tác nhân Thị trường Thuần túy tại Độ rộng Cố định Chuẩn (Fixed-Width Market Drivers, N = 4,590)",
        font_size=8.5,
    )

    add_p(
        doc,
        "Cả Bảng 4.3 và Bảng 4.4 đều cho thấy sự nhất quán tuyệt đối về mặt thống kê: (i) Biến động giá thực tế 24h (feat_rvol_24h) làm tăng mạnh "
        "cả IL_Magnitude (β = 0.0946, t = 5.63, p = 1.80e-08 trên mẫu cố định độ rộng) và LVR_Cumulative (β = 0.1623, t = 18.73, p = 2.92e-78, "
        "giải thích tới R² = 57.37% phương sai của LVR); (ii) Biến tương tác vol_x_narrow có t = 18.98 (p = 2.42e-80) đối với IL và t = -2.64 "
        "(p = 0.0084) đối với Net_Return_vs_HODL, khẳng định việc duy trì khoảng thanh khoản hẹp trong lúc thị trường biến động cao bào mòn trực tiếp "
        "lợi nhuận ròng của LP; và (iii) Trong phương trình Net_Return_vs_HODL ở Bảng 4.3, tỷ số Volume/TVL có hệ số β = -0.0072 (p = 0.0330), "
        "chứng minh rằng các đợt khối lượng giao dịch tăng đột biến đi kèm biến động giá chủ yếu là dòng lệnh kinh doanh chênh lệch giá độc hại (toxic arbitrage flow)."
    )

    doc.add_heading("4.4. Hồi quy Phân vị (Quantile Regression) & Phân rã Phi tuyến TreeSHAP", level=2)
    df_qr = pd.read_csv(TABLES_DIR / "rq1_quantile_regressions.csv")
    qr_rows = []
    for _, r in df_qr[df_qr["term"].isin(["feat_rvol_24h", "range_width_pct", "vol_x_narrow", "feat_volume_tvl_ratio_24h"])].iterrows():
        qr_rows.append([
            f"τ = {r['quantile']:.2f}",
            r["term"],
            fmt_num(r["coef"], 6),
            fmt_num(r["std_err"], 6),
            f"{r['t_stat']:.2f}",
            f"{r['p_value']:.2e}" if r["p_value"] < 0.001 else f"{r['p_value']:.4f}",
            f"{r['pseudo_r2']:.4f}",
        ])
    add_styled_table(
        doc,
        headers=["Phân vị (τ)", "Biến giải thích trọng tâm", "Hệ số (β_τ)", "Sai số chuẩn", "Thống kê t", "Giá trị p", "Pseudo-R²"],
        rows=qr_rows,
        caption="Bảng 4.5: Sự khuếch đại độ nhạy rủi ro đuôi của IL qua Hồi quy Phân vị tại τ ∈ {0.50, 0.90, 0.95}",
        font_size=9.0,
    )

    df_shap = pd.read_csv(TABLES_DIR / "rq1_shap_importance.csv")
    shap_rows = [
        [r["feature"], fmt_num(r["mean_abs_shap"], 5), f"{r['relative_share_pct']:.2f}%"]
        for _, r in df_shap.iterrows()
    ]
    add_styled_table(
        doc,
        headers=["Đặc trưng Thị trường (Tại độ rộng chuẩn)", "Mean |SHAP Value|", "Tỷ trọng Đóng góp Tương đối (%)"],
        rows=shap_rows,
        caption="Bảng 4.6: Phân rã mức độ quan trọng phi tuyến của các tác nhân thị trường bằng TreeSHAP",
        font_size=9.5,
    )

    add_p(
        doc,
        "Bảng 4.5 và Bảng 4.6 làm sáng tỏ cấu trúc phi tuyến và bất đối xứng của rủi ro IL: Hệ số của biến tương tác vol_x_narrow tăng vọt "
        "từ 0.000265 ở trung vị (τ = 0.50) lên 0.003481 ở phân vị 90% và đạt 0.004772 ở phân vị 95% (gấp 18.0 lần trung vị), đồng thời "
        "Pseudo-R² tăng từ 7.15% lên 37.63%. Hơn nữa, phân tích TreeSHAP trên mô hình Gradient Boosted Trees chỉ ra rằng biến động chiều giảm "
        "(feat_downside_vol_24h) đóng góp tới 46.18% tổng giá trị giải thích SHAP, vượt xa biến động hai chiều thông thường (feat_rvol_24h, 18.21%) "
        "và tỷ suất phí (feat_fee_apr_24h, 14.92%)."
    )

    add_figure(
        doc,
        FIGURES_DIR / "rq1_shap_feature_importance.png",
        "Hình 4.2: Tỷ trọng đóng góp phi tuyến của các tác nhân thị trường đối với Impermanent Loss 24h (TreeSHAP Attribution)",
        width_inches=5.5,
    )

    doc.add_page_break()

    # =========================================================================
    # CHƯƠNG 5: KẾT QUẢ THỰC NGHIỆM RQ2 — DỰ BÁO PHÂN PHỐI IL
    # =========================================================================
    doc.add_heading("CHƯƠNG 5: KẾT QUẢ THỰC NGHIỆM RQ2 — DỰ BÁO PHÂN PHỐI IMPERMANENT LOSS NGOẠI MẪU", level=1)

    doc.add_heading("5.1. Thiết kế Kiểm định 8-Fold Purged Walk-Forward & Ba Lớp Mô hình", level=2)
    add_p(
        doc,
        "Để đánh giá năng lực dự báo ngoại mẫu (Out-of-Sample – OOS) một cách trung thực nhất trên chuỗi thời gian 2021–2025, đồ án triển khai "
        "cơ chế 8-Fold Expanding-Window Purged Walk-Forward cho cả 3 chân trời dự báo H ∈ {1 ngày (24h), 7 ngày (168h), 30 ngày (720h)}. "
        "Giữa tập Huấn luyện (Train), tập Hiệu chỉnh (Validation) và tập Kiểm định (Test) của mỗi fold luôn có một khoảng đệm cách ly "
        "purge_hours = H nhằm đảm bảo nhãn tương lai của tập đứng trước không bao giờ chồng lấn sang tập đứng sau."
    )
    add_p(
        doc,
        "Nhằm đảm bảo tính minh bạch học thuật tuyệt đối khi kiểm định giả thuyết H2.1, đồ án báo cáo độc lập 3 mô hình dự báo điểm:"
    )
    add_bullet(
        doc,
        "1. Mô hình Giải tích Truyền thống (Analytical_Baseline): ",
        "Áp dụng công thức kỳ vọng giải tích của tổn thất tạm thời Concentrated Liquidity dưới giả định tỷ giá tuân theo chuyển động Brown hình học "
        "với tham số độ biến động bằng biến động thực tế lịch sử (Historical Realized Volatility).",
    )
    add_bullet(
        doc,
        "2. Mô hình Học máy Thuần túy Độc lập (Pure_ML): ",
        "Mô hình Gradient Boosting huấn luyện trên thang logarit log(IL + ε) (kèm hệ số hiệu chỉnh chệch Duan's Smearing chuẩn hóa trên tập Validation) "
        "chỉ sử dụng 26 đặc trưng chuỗi thời gian nhân quả tại Bảng 3.3, hoàn toàn không sử dụng đầu vào Analytical_Baseline và không trộn trọng số.",
    )
    add_bullet(
        doc,
        "3. Mô hình Kết hợp (Hybrid_Ensemble): ",
        "Tổ hợp lồi tối ưu giữa dự báo học máy và mỏ neo giải tích với trọng số α ∈ [0, 1] được lựa chọn hoàn toàn trên tập Validation của từng fold.",
    )

    doc.add_heading("5.2. Kết quả So sánh Dự báo Điểm, Kiểm định Diebold–Mariano HLN & Conformal Coverage", level=2)
    df_rq2 = pd.read_csv(TABLES_DIR / "rq2_forecast_comparison.csv")
    rq2_rows = []
    for _, r in df_rq2.iterrows():
        rq2_rows.append([
            r["pool_key"],
            r["horizon"],
            f"{int(r['n_test'])} ({int(r['n_eff_test'])})",
            fmt_num(r["baseline_rmse"], 5),
            fmt_num(r["pure_ml_rmse"], 5),
            f"{r['pure_ml_improvement_pct']:+.2f}%",
            fmt_num(r["ml_rmse"], 5),
            f"{r['rmse_improvement_pct']:+.2f}%",
            f"{r['pure_ml_dm_stat']:.2f} ({r['pure_ml_dm_p_value']:.4f})",
            f"{r['ml_raw_coverage_q_90']*100:.1f}%",
            f"{r['ml_coverage_q_90']*100:.1f}%",
        ])
    add_styled_table(
        doc,
        headers=[
            "Pool", "Chân trời", "N_test (n_eff)", "Baseline RMSE", "Pure ML RMSE",
            "Pure ML Δ%", "Hybrid RMSE", "Hybrid Δ%", "DM-HLN (p-val)", "Raw Cov q90", "Conformal q90",
        ],
        rows=rq2_rows,
        caption="Bảng 5.1: So sánh hiệu năng dự báo Ngoại mẫu tổng hợp qua 8 Fold Walk-Forward (Analytical Baseline vs Pure ML vs Hybrid Ensemble)",
        font_size=8.0,
    )

    add_p(
        doc,
        "Kết quả tại Bảng 5.1 xác nhận toàn bộ ba giả thuyết nghiên cứu H2.1, H2.2 và H2.3:"
    )
    add_bullet(
        doc,
        "Khẳng định giả thuyết H2.1 (Sự vượt trội của Học máy ở chân trời ngắn và trung hạn): ",
        "Tại chân trời 1 ngày (24h), mô hình học máy độc lập Pure_ML đánh bại mô hình giải tích Analytical_Baseline trên cả 4/4 pool: "
        "giảm 16.94% RMSE trên WETH/USDC 0.05% (thống kê DM-HLN = 2.86, p = 0.0042 trên n_eff = 832 cửa sổ độc lập), giảm 16.33% RMSE trên "
        "WETH/USDC 0.30% (DM-HLN = 2.79, p = 0.0053), giảm 9.84% RMSE trên USDC/USDT 0.01% (p = 0.0707) và giảm 0.50% trên wstETH/ETH 0.01%. "
        "Ở chân trời 7 ngày (168h), mức cải thiện RMSE của Pure_ML trên hai pool WETH/USDC càng ấn tượng hơn, đạt 21.67% (p = 0.0014) và 17.44% (p = 0.0097).",
    )
    add_bullet(
        doc,
        "Khẳng định giả thuyết H2.2 (Động học theo chân trời dự báo và công suất thống kê): ",
        "Ở chân trời 1 ngày và 7 ngày, thông tin vi cấu trúc thị trường (biến động chiều giảm, độ lệch giá CEX–DEX, tốc độ rút thanh khoản) mang lại "
        "lợi thế dự báo rất lớn cho mô hình học máy. Khi kéo dài tới 30 ngày (720h), quá trình khuếch tán giá dài hạn khiến lợi thế vi cấu trúc giảm dần "
        "(cải thiện 14.40% trên WETH/USDC 0.05%, 1.78% trên WETH/USDC 0.30% và 27.72% trên wstETH/ETH 0.01%). Nhờ mở rộng dữ liệu 2021–2025 với 8 fold, "
        "số quan sát độc lập không chồng lấn ở chân trời 30d đạt n_eff ∈ [10, 27], đảm bảo điều kiện hợp lệ của kiểm định Diebold–Mariano HLN.",
    )
    add_bullet(
        doc,
        "Khẳng định giả thuyết H2.3 (Hiệu quả của Split Conformal Quantile Calibration): ",
        "Trước khi hiệu chỉnh, mô hình Quantile GBDT ở phân vị q90 bị thiếu độ phủ trên một số kịch bản (ví dụ 77.7% trên WETH/USDC 0.05% 30d và "
        "82.5% trên USDC/USDT 0.01% 1d). Sau khi áp dụng Split Conformal Calibration tái ước lượng trên tập Validation của từng fold, độ bao phủ thực nghiệm "
        "trung bình toàn cục đạt 88.7% (rất sát mức mục tiêu lý thuyết 90.0%; cụ thể ở chân trời 1d đạt 89.4% trên WETH/USDC 0.05%, 90.7% trên WETH/USDC 0.30% "
        "và 89.0% trên USDC/USDT 0.01%).",
    )

    add_figure(
        doc,
        FIGURES_DIR / "rq2_quantile_forecast_weth_usdc_005.png",
        "Hình 5.1: Dải dự báo Phân vị Conformal (q50, q90, q95) so với Impermanent Loss thực tế ngoại mẫu trên Pool WETH/USDC 0.05%",
        width_inches=6.0,
    )
    add_figure(
        doc,
        FIGURES_DIR / "rq2_quantile_forecast_weth_usdc_030.png",
        "Hình 5.2: Dải dự báo Phân vị Conformal (q50, q90, q95) so với Impermanent Loss thực tế ngoại mẫu trên Pool WETH/USDC 0.30%",
        width_inches=6.0,
    )

    doc.add_page_break()

    # =========================================================================
    # CHƯƠNG 6: KẾT QUẢ THỰC NGHIỆM RQ3 — BACKTEST CHIẾN LƯỢC LP ĐỘNG
    # =========================================================================
    doc.add_heading("CHƯƠNG 6: KẾT QUẢ THỰC NGHIỆM RQ3 — ĐÁNH GIÁ CHIẾN LƯỢC QUẢN TRỊ THANH KHOẢN ĐỘNG", level=1)

    doc.add_heading("6.1. Thiết kế 4 Chiến lược Quản trị Thanh khoản & Mô hình Chi phí Thực tế", level=2)
    add_p(
        doc,
        "Trên từng cửa sổ kiểm định ngoại mẫu của 8 fold Walk-Forward, đồ án mô phỏng bốn chiến lược quản trị vị thế LP với vốn khởi tạo chuẩn hóa "
        "V0 = 100,000 USD. Mỗi lần tái cân bằng (Rebalance: thu hồi thanh khoản cũ, hoán đổi token về tỷ lệ cân bằng tại giá mới và đúc vị thế mới), "
        "danh mục phải gánh chịu đồng thời hai khoản chi phí ma sát thực tế trên chuỗi:"
    )
    add_formula_block(
        doc,
        "TxCost_t = GasCost_USD(GasUnits = 350,000, GasPrice_t, ETH_Price_t) / V_t  +  Slippage_t(FeeTier, LiquidityRatio)",
        "6.1",
    )
    add_p(doc, "Bốn chiến lược được so sánh trực tiếp bao gồm:")
    add_bullet(
        doc,
        "1. Chiến lược LP Tĩnh (Static_LP): ",
        "Cung cấp thanh khoản vào độ rộng chuẩn ban đầu (w = ±10% cho pool biến động, w = ±2% cho pool ổn định) và nắm giữ xuyên suốt toàn bộ fold "
        "mà không bao giờ tái cân bằng (TxCost = 0, nhưng chịu rủi ro đứng ngoài thị trường khi giá trượt ra ngoài biên [Pa, Pb]).",
    )
    add_bullet(
        doc,
        "2. Chiến lược Tái cân bằng Định kỳ (Periodic_Rebalance): ",
        "Tự động căn giữa lại vùng thanh khoản (re-center) sau mỗi chu kỳ cố định 7 ngày (168 giờ) bất kể trạng thái thị trường.",
    )
    add_bullet(
        doc,
        "3. Quy tắc Chỉ Tối thiểu hóa IL (IL_Min_Rule): ",
        "Sử dụng tín hiệu dự báo phân vị đuôi q90_conformal từ RQ2 để lập tức mở rộng hoặc thu hẹp vùng thanh khoản khi rủi ro IL dự báo vượt ngưỡng "
        "phân vị trên tập Validation (với thời gian chờ tối thiểu 24h), nhưng bỏ qua hoàn toàn phép tính chi phí giao dịch và lợi ích phí bị mất.",
    )
    add_bullet(
        doc,
        "4. Chiến lược Thỏa dụng Ròng có Kiểm soát Chi phí (Signal_Net_Utility – Đề xuất): ",
        "Chỉ thực hiện tái cân bằng khi Lợi ích Ròng Kỳ vọng (Expected Net Utility Gain = Phần phí giao dịch khôi phục được khi thoát trạng thái "
        "Out-of-Range + Phần giảm tổn thất đuôi kỳ vọng − Phần phạt tăng IL khi thu hẹp range) vượt qua ngưỡng cản chi phí giao dịch "
        "γ · (GasCost_t + DynamicSlippage_t).",
    )

    doc.add_heading("6.2. Kết quả Backtest Ngoại mẫu qua 8 Fold Walk-Forward", level=2)
    df_rq3 = pd.read_csv(TABLES_DIR / "rq3_backtest_comparison.csv")
    rq3_rows = []
    for _, r in df_rq3.iterrows():
        rq3_rows.append([
            r["pool_key"],
            r["strategy"],
            f"{r['net_return_vs_hodl_pct']:+.2f}% (±{r['net_return_ci95_pct']:.2f}%)",
            f"{r['hedged_net_return_pct']:+.2f}%",
            f"{r['cum_fees_pct']:.2f}%",
            f"{r['realized_il_pct']:+.2f}%",
            f"{r['tx_cost_gas_slippage_pct']:.2f}%",
            f"{r['rebalance_count']:.1f}",
            f"{r['in_range_time_pct']:.1f}%",
            f"{r['sharpe_vs_hodl']:.2f}",
            f"{r['max_drawdown_pct']:.2f}%",
        ])
    add_styled_table(
        doc,
        headers=[
            "Pool", "Chiến lược", "Net Ret vs HODL (95% CI)", "Hedged Ret",
            "Phí lũy kế", "IL thực hiện", "Chi phí Tx", "Số lần Reb", "In-Range %", "Sharpe", "MDD %",
        ],
        rows=rq3_rows,
        caption="Bảng 6.1: Kết quả Backtest Ngoại mẫu trung bình trên mỗi Fold (8 Folds Walk-Forward, V0 = 100,000 USD)",
        font_size=8.0,
    )

    add_p(
        doc,
        "Kết quả thực nghiệm tại Bảng 6.1 chứng minh trọn vẹn các giả thuyết H3.1, H3.2 và H3.4, đồng thời làm nổi bật những phát hiện cốt lõi:"
    )
    add_bullet(
        doc,
        "Thắng lợi của Signal_Net_Utility trên các Pool Biến động (H3.1 & H3.2): ",
        "Trên WETH/USDC 0.05%, chiến lược Static_LP chỉ ở trong vùng hoạt động 41.0% thời gian (thu được 8.74% phí/fold) và đạt lợi nhuận ròng vs HODL "
        "+0.77%/fold. Chiến lược Periodic_Rebalance và IL_Min_Rule tuy duy trì tỷ lệ In-Range cao (93.2%–100%), nhưng do tái cân bằng quá dày đặc "
        "(14.0 đến 24.3 lần/fold, tiêu tốn 1.98%–4.06% vốn cho phí gas + slippage và liên tục khóa chặt khoản lỗ IL đúng đáy/đỉnh biến động) nên "
        "bị lỗ ròng nặng nề (-5.58%/fold và -4.09%/fold). Ngược lại, Signal_Net_Utility chỉ tái cân bằng chọn lọc trung bình 5.0 lần/fold khi vị thế "
        "bị trượt khỏi vùng giá và lợi ích phí khôi phục lớn hơn chi phí giao dịch, nhờ đó duy trì 99.99% thời gian In-Range, thu 17.33% phí/fold, "
        "giảm một nửa Max Drawdown (từ 14.87% xuống 7.26%) và đạt lợi nhuận ròng cao nhất +1.21%/fold (+1.18%/fold trên WETH/USDC 0.30%).",
    )
    add_bullet(
        doc,
        "Sự tối ưu của quyết định 'Không hành động' trên Pool Correlated và Stablecoin (H3.4): ",
        "Trên wstETH/ETH 0.01% và USDC/USDT 0.01%, vùng thanh khoản hẹp ±2% duy trì 100.0% thời gian In-Range xuyên suốt các cửa sổ kiểm định. "
        "Thuật toán Signal_Net_Utility tự động đánh giá lợi ích ròng của việc tái cân bằng bằng 0 (nhỏ hơn chi phí giao dịch dương) nên quyết định "
        "không tái cân bằng bất kỳ lần nào (0.0 lần), đạt hiệu năng tối ưu ngang bằng Static_LP (+0.72%/fold với Sharpe 5.92 trên wstETH/ETH; "
        "+0.49%/fold với Sharpe 12.51 trên USDC/USDT), trong khi Periodic_Rebalance bị chuyển từ lãi thành lỗ (-0.28% và -1.24%/fold) chỉ vì trả phí gas định kỳ vô ích.",
    )
    add_bullet(
        doc,
        "So sánh sâu sắc giữa Unhedged Return (Fee − IL − Cost) và Delta-Hedged Return (Fee − LVR − Cost): ",
        "Trên hai pool biến động WETH/USDC, lợi nhuận ròng không phòng hộ (Unhedged Net Return vs HODL) của Signal_Net_Utility mang dấu dương (+1.21% và +1.18%/fold), "
        "nhưng lợi nhuận phòng hộ delta liên tục (Hedged Net Return = Fee − LVR − Cost) lại mang dấu âm (-6.80% và -6.00%/fold). Điều này phù hợp hoàn toàn với "
        "lý thuyết của Milionis et al. (2022): LVR tích lũy mọi dao động nhỏ dọc theo đường đi của giá (lên tới 23.29%–23.68%/fold), nên một LP phòng hộ "
        "delta liên tục sẽ khóa lỗ ở mọi nhịp nhiễu nội giờ; trái lại, một LP không phòng hộ được hưởng lợi từ tính chất hồi quy trung bình (mean-reversion) "
        "của tỷ giá giữa các chu kỳ, khiến IL thực hiện thấp hơn đáng kể so với tổng LVR. Ngược lại, trên wstETH/ETH và USDC/USDT, cả Unhedged Return "
        "và Delta-Hedged Return đều dương (+0.74% và +0.49%/fold) vì biến động nội giờ cực thấp.",
    )

    add_figure(
        doc,
        FIGURES_DIR / "rq3_equity_curve_weth_usdc_005.png",
        "Hình 6.1: Đường cong Lợi nhuận ròng lũy kế so với HODL của 4 Chiến lược trên Pool WETH/USDC 0.05%",
        width_inches=6.0,
    )
    add_figure(
        doc,
        FIGURES_DIR / "rq3_equity_curve_weth_usdc_030.png",
        "Hình 6.2: Đường cong Lợi nhuận ròng lũy kế so với HODL của 4 Chiến lược trên Pool WETH/USDC 0.30%",
        width_inches=6.0,
    )
    add_figure(
        doc,
        FIGURES_DIR / "rq3_equity_curve_wsteth_eth_001.png",
        "Hình 6.3: Đường cong Lợi nhuận ròng lũy kế so với HODL của 4 Chiến lược trên Pool wstETH/ETH 0.01%",
        width_inches=6.0,
    )

    doc.add_heading("6.3. Phân tích Độ nhạy theo Kịch bản Chi phí Gas (5 Gwei vs 20 Gwei vs 60 Gwei)", level=2)
    df_gas = pd.read_csv(TABLES_DIR / "rq3_gas_sensitivity.csv")
    gas_rows = []
    for _, r in df_gas.iterrows():
        gas_rows.append([
            r["pool_key"],
            r["gas_scenario"],
            r["strategy"],
            f"{int(r['rebalance_count'])}",
            f"{r['tx_cost_pct']:.2f}%",
            f"{r['net_return_vs_hodl_pct']:+.2f}%",
            f"{r['hedged_net_return_pct']:+.2f}%",
        ])
    add_styled_table(
        doc,
        headers=["Pool", "Kịch bản Gas", "Chiến lược", "Tổng số lần Reb (8 Folds)", "Tổng Chi phí Tx (%)", "Tổng Net Ret vs HODL (%)", "Tổng Hedged Ret (%)"],
        rows=gas_rows,
        caption="Bảng 6.2: Phân tích độ nhạy hiệu năng chiến lược lũy kế dưới 3 kịch bản chi phí Gas (Giả thuyết H3.3)",
        font_size=8.5,
    )

    add_p(
        doc,
        "Bảng 6.2 khẳng định giả thuyết H3.3: Khi mạng Ethereum chuyển từ kịch bản phí thấp (5 Gwei – tương đương thời điểm mạng rỗi hoặc môi trường Layer-2) "
        "sang kịch bản nghẽn mạng (60 Gwei), tổng chi phí giao dịch của chiến lược Periodic_Rebalance trên WETH/USDC 0.05% tăng vọt từ 0.84% lên 6.59%, "
        "kéo lợi nhuận lũy kế từ +0.82% xuống lỗ -4.93%. Trong khi đó, chiến lược Signal_Net_Utility giữ chi phí giao dịch ở mức thấp hơn 2.5 lần "
        "(chỉ 0.33% ở 5 Gwei và 2.60% ở 60 Gwei), bảo toàn tổng lợi nhuận lũy kế vượt trội (+12.63% ở 5 Gwei và +10.41% ở 60 Gwei)."
    )

    doc.add_page_break()

    # =========================================================================
    # CHƯƠNG 7: KẾT LUẬN, HÀM Ý QUẢN TRỊ VÀ HƯỚNG PHÁT TRIỂN
    # =========================================================================
    doc.add_heading("CHƯƠNG 7: KẾT LUẬN, HÀM Ý QUẢN TRỊ RỦI RO VÀ HƯỚNG PHÁT TRIỂN", level=1)

    doc.add_heading("7.1. Tổng kết Kiểm định 12 Giả thuyết Nghiên cứu", level=2)
    concl_rows = [
        ["H1.1", "Biến động giá làm tăng IL & LVR", "ỦNG HỘ MẠNH", "feat_rvol_24h có p = 1.80e-08 (IL) và p = 2.92e-78, R² = 57.4% (LVR) trên mẫu cố định độ rộng."],
        ["H1.2", "Range hẹp khuếch đại rủi ro đuôi & OOR", "ỦNG HỘ MẠNH", "Hệ số tương tác vol_x_narrow ở phân vị 95% lớn gấp 18.0 lần so với tại trung vị (p < 1e-90)."],
        ["H1.3", "Pool Stable/Correlated có IL cực thấp trừ khi depeg", "ỦNG HỘ MẠNH", "Median IL ~ 0.000002%, nhưng sự kiện SVB Depeg 03/2023 đẩy Mean IL trên USDC/USDT tăng gấp 3,600 lần."],
        ["H1.4", "Volume đột biến đi kèm lựa chọn bất lợi", "ỦNG HỘ (CÓ ĐIỀU KIỆN)", "Volume/TVL có β = -0.0072 (p = 0.033) lên Net Return trừ khi chọn bậc phí 0.30% và range đủ rộng (±20%)."],
        ["H1.5", "Bất đối xứng theo chế độ thị trường & chiều giá", "ỦNG HỘ MẠNH", "Downside Volatility chiếm 46.18% tỷ trọng giải thích phi tuyến TreeSHAP đối với IL 24h."],
        ["H2.1", "Mô hình ML vượt Baseline giải tích ở chân trời 1d", "ỦNG HỘ MẠNH", "Pure_ML giảm 16.94% RMSE (p = 0.0042) và 16.33% RMSE (p = 0.0053) trên hai pool WETH/USDC."],
        ["H2.2", "Biến thiên hiệu năng theo chân trời 1d, 7d, 30d", "ỦNG HỘ", "Cải thiện mạnh nhất ở 1d–7d (lên tới 21.67% RMSE); kiểm định DM-HLN hợp lệ với n_eff ≥ 10 ở mọi chân trời."],
        ["H2.3", "Split Conformal chuẩn hóa độ bao phủ phân vị", "ỦNG HỘ MẠNH", "Độ bao phủ thực nghiệm ngoại mẫu tại q90 tăng từ 87.1% lên 88.7% (mục tiêu lý thuyết 90.0%)."],
        ["H3.1", "Signal_Net_Utility vượt trội Periodic_Rebalance", "ỦNG HỘ MẠNH", "Đạt +1.21% và +1.18%/fold trên WETH/USDC so với -5.58% và -1.27%/fold của Periodic_Rebalance."],
        ["H3.2", "Quy tắc chỉ giảm IL (IL_Min_Rule) gây lỗ ròng", "ỦNG HỘ MẠNH", "IL_Min_Rule tái cân bằng 21.8–24.3 lần/fold, tốn 3.22%–4.06% chi phí giao dịch và lỗ -3.36% đến -4.09%/fold."],
        ["H3.3", "Chi phí Gas quyết định tần suất tái cân bằng", "ỦNG HỘ MẠNH", "Ở mức 60 Gwei, Periodic_Rebalance mất 6.59% vốn vì phí giao dịch trong khi Signal_Net_Utility giữ vững lợi nhuận."],
        ["H3.4", "Phân hóa chiến lược tối ưu theo cấu trúc Pool", "ỦNG HỘ MẠNH", "Quản trị động tạo giá trị lớn trên pool biến động; giữ nguyên vị thế (Static LP) tối ưu trên pool ổn định."],
    ]
    add_styled_table(
        doc,
        headers=["Giả thuyết", "Nội dung cốt lõi", "Kết luận Kiểm định", "Bằng chứng Định lượng Thực nghiệm"],
        rows=concl_rows,
        caption="Bảng 7.1: Bảng tổng hợp kết quả kiểm định 12 giả thuyết nghiên cứu của đồ án",
        font_size=8.5,
    )

    doc.add_heading("7.2. Khuyến nghị Thực tiễn cho Nhà Cung cấp Thanh khoản (LP) & Giao thức AMM", level=2)
    add_bullet(
        doc,
        "1. Đối với các cặp tài sản biến động mạnh (ETH/USDC, WBTC/USDC): ",
        "Không bao giờ sử dụng chiến lược đặt lệnh cực hẹp (±1%, ±2%) kèm tái cân bằng theo lịch cố định trên Ethereum Mainnet. Thay vào đó, "
        "LP nên khởi tạo độ rộng vừa phải (±10% đến ±20%) và chỉ kích hoạt tái cân bằng khi vị thế đã trượt khỏi biên thanh khoản đồng thời "
        "phần phí dự kiến thu hồi được trong 7 ngày tới lớn hơn ít nhất 1.2 lần tổng chi phí Gas và Slippage.",
    )
    add_bullet(
        doc,
        "2. Đối với các cặp tài sản tương quan (LST/ETH) và Stablecoin: ",
        "Lựa chọn vùng thanh khoản ±2% với chiến lược thụ động (Static LP) mang lại tỷ suất lợi nhuận điều chỉnh rủi ro cao nhất (Sharpe 5.92–12.51). "
        "Tuy nhiên, cần tích hợp bộ cảnh báo xác suất vượt ngưỡng IL và độ lệch chốt tỷ giá (stablecoin peg deviation) để tự động rút thanh khoản "
        "khi xảy ra khủng hoảng hệ thống tương tự sự kiện SVB tháng 03/2023.",
    )

    doc.add_heading("7.3. Hạn chế của Nghiên cứu và Hướng Phát triển Tiếp theo", level=2)
    add_p(
        doc,
        "Mặc dù đồ án đã sử dụng dữ liệu thực tế đa chu kỳ 2021–2025 và tuân thủ nghiêm ngặt các tiêu chuẩn chống rò rỉ tương lai, nghiên cứu vẫn "
        "còn một số giới hạn kỹ thuật mở ra hướng phát triển tiếp theo cho các công trình sau:"
    )
    add_bullet(
        doc,
        "Độ phân giải thời gian theo Block / Tick-by-Tick: ",
        "Nghiên cứu hiện tại định giá danh mục và ước lượng LVR trên lưới thời gian đóng nến 1 giờ (hourly snapshots). Việc mở rộng xuống dữ liệu "
        "sự kiện từng giao dịch Swap/Mint/Burn ở cấp độ từng block (12 giây trên Ethereum) sẽ giúp tách biệt chính xác hơn nữa giữa dòng lệnh "
        "nhỏ lẻ (noise traders) và dòng lệnh MEV / Just-In-Time (JIT) Liquidity.",
    )
    add_bullet(
        doc,
        "Mở rộng sang các mạng Layer-2 (Arbitrum, Optimism, Base) và Uniswap v4 Hooks: ",
        "Kết quả phân tích độ nhạy Gas ở kịch bản 5 Gwei cho thấy tiềm năng sinh lời rất lớn khi chi phí tái cân bằng tiệm cận 0. Việc triển khai "
        "mô hình Signal_Net_Utility dưới dạng hợp đồng thông minh Dynamic Fee / Dynamic Range Hook trên Uniswap v4 hoặc trên các mạng Layer-2 "
        "là bước ứng dụng thực tế giàu triển vọng.",
    )

    doc.add_page_break()

    # =========================================================================
    # TÀI LIỆU THAM KHẢO (REFERENCES)
    # =========================================================================
    doc.add_heading("TÀI LIỆU THAM KHẢO (REFERENCES)", level=1)
    refs = [
        "Adams, H., Zinsmeister, N., & Robinson, D. (2020). Uniswap v2 Core. Uniswap Protocol Technical Whitepaper.",
        "Adams, H., Zinsmeister, N., Salem, M., Keefer, R., & Robinson, D. (2021). Uniswap v3 Core. Uniswap Protocol Technical Whitepaper.",
        "angeris, G., Kao, H. T., Chiang, R., Noyes, C., & Chitra, T. (2021). An analysis of Uniswap markets. Cryptoeconomic Systems, 1(1).",
        "Capponi, A., & Jia, R. (2021). The adoption of blockchain-based decentralized exchanges. arXiv preprint arXiv:2103.08842.",
        "Cartea, Á., Drissi, F., & Monga, M. (2023). Decentralized finance and automated market making: Execution and speculation. SSRN Electronic Journal.",
        "Diebold, F. X., & Mariano, R. S. (1995). Comparing predictive accuracy. Journal of Business & Economic Statistics, 13(3), 253–263.",
        "Duan, N. (1983). Smearing estimate: A nonparametric retransformation method. Journal of the American Statistical Association, 78(383), 605–610.",
        "Harvey, D., Leybourne, S., & Newbold, P. (1997). Testing the equality of prediction mean squared errors. International Journal of Forecasting, 13(2), 281–291.",
        "Heimbach, L., Schertenleib, E., & Wattenhofer, R. (2022). Risks and returns of Uniswap v3 liquidity providers. In Proceedings of the 4th ACM Conference on Advances in Financial Technologies (AFT '22) (pp. 89–101).",
        "Koenker, R., & Bassett Jr, G. (1978). Regression quantiles. Econometrica, 46(1), 33–50.",
        "Loesch, S., Hindman, N., Richardson, M. B., & Welch, N. (2021). Impermanent loss in Uniswap v3. arXiv preprint arXiv:2111.09192.",
        "López de Prado, M. (2018). Advances in Financial Machine Learning. John Wiley & Sons.",
        "Lundberg, S. M., & Lee, S. I. (2017). A unified approach to interpreting model predictions. In Advances in Neural Information Processing Systems (NeurIPS) (Vol. 30).",
        "Milionis, J., Moallemi, C. C., Roughgarden, T., & Zhang, A. L. (2022). Automated market making and loss-versus-rebalancing. arXiv preprint arXiv:2208.06046.",
        "Milionis, J., Moallemi, C. C., & Roughgarden, T. (2023). Automated market making and arbitrage profits in the presence of fees. In Financial Cryptography and Data Security (FC 2023).",
        "Newey, W. K., & West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. Econometrica, 55(3), 703–708.",
        "Romano, Y., Patterson, E., & Candès, E. (2019). Conformalized quantile regression. In Advances in Neural Information Processing Systems (NeurIPS) (Vol. 32).",
    ]
    for ref in refs:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Cm(1.0)
        p.paragraph_format.first_line_indent = Cm(-1.0)
        p.paragraph_format.space_after = Pt(5)
        r = p.add_run(ref)
        r.font.name = "Times New Roman"
        r.font.size = Pt(11.5)

    OUTPUT_DOCX.parent.mkdir(parents=True, exist_ok=True)
    alt_path = REPORTS_DIR / "Do_An_Tot_Nghiep_UniswapV3_IL_LVR_MUC_LUC.docx"

    # Lưu bản tài liệu có mục lục
    doc.save(str(alt_path))

    saved_path = alt_path
    try:
        doc.save(str(OUTPUT_DOCX))
        saved_path = OUTPUT_DOCX
    except PermissionError:
        print(f"LƯU Ý: File {OUTPUT_DOCX.name} đang mở trong ứng dụng khác (Word) nên chưa thể ghi đè trực tiếp.")
        print(f"Bản cập nhật đầy đủ có Mục lục đã được lưu tại: {alt_path.name}")

    return saved_path


if __name__ == "__main__":
    out_path = build_Thesis_Document()
    print(f"Created thesis Word document at: {out_path} ({out_path.stat().st_size:,} bytes)")
