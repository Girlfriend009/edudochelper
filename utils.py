# utils.py
import io
import uuid
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from jinja2 import Template
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent
FONT_PATH = BASE_DIR / "fonts" / "DejaVuSans.ttf"
FONT_BOLD_PATH = BASE_DIR / "fonts" / "DejaVuSans-Bold.ttf"
FONT_ITALIC_PATH = BASE_DIR / "fonts" / "DejaVuSans-Oblique.ttf"

def register_font():
    try:
        if FONT_PATH.exists():
            pdfmetrics.registerFont(TTFont("DejaVuSans", str(FONT_PATH)))
        if FONT_BOLD_PATH.exists():
            pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(FONT_BOLD_PATH)))
        else:
            # fallback к обычному шрифту, если нет жирного
            pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(FONT_PATH)))
        if FONT_ITALIC_PATH.exists():
            pdfmetrics.registerFont(TTFont("DejaVuSans-Italic", str(FONT_ITALIC_PATH)))
        else:
            # fallback к обычному шрифту, если нет курсива
            pdfmetrics.registerFont(TTFont("DejaVuSans-Italic", str(FONT_PATH)))
    except Exception as e:
        print(f"Ошибка загрузки шрифта: {e}")

def create_pdf_from_template(template_text, data_dict, signature_path=None):
    register_font()
    jinja_tpl = Template(template_text or "")
    rendered = jinja_tpl.render(**(data_dict or {}))

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Отступы
    left_margin = 25 * mm
    right_margin = 25 * mm
    top_margin = height - 30 * mm
    bottom_margin = 30 * mm

    # --- ВСТАВКА ЛОГОТИПА В ШАПКУ ---
    logo_path = BASE_DIR / "static" / "img" / "logo.png"  # можно .jpg
    if logo_path.exists():
        # Вставляем логотип в левый верхний угол
        p.drawImage(str(logo_path), left_margin, height - 30 * mm, width=50 * mm, height=50 * mm, preserveAspectRatio=True, mask='auto')
        y = top_margin - 60 * mm  # сдвигаем текст ниже, чтобы он не перекрывал логотип
    else:
        y = top_margin  # если логотипа нет — начинаем с верхнего отступа

    # Устанавливаем шрифт по умолчанию
    try:
        p.setFont("DejaVuSans", 12)
    except:
        p.setFont("Helvetica", 12)

    # Разбиваем текст на строки
    lines = rendered.splitlines()

    for line in lines:
        # Пропускаем пустые строки
        if not line.strip():
            y -= 6 * mm
            continue

        # Обработка стилей: **жирный**, *курсив*, _подчёркнутый_
        line = line.strip()

        # Проверка на заголовок: строка вида "**Текст**"
        if line.startswith("**") and line.endswith("**"):
            content = line[2:-2]
            try:
                p.setFont("DejaVuSans-Bold", 14)
            except:
                p.setFont("Helvetica-Bold", 14)
            # Центрируем заголовок
            text_width = p.stringWidth(content, p._fontname, p._fontsize)
            x_pos = (width - text_width) / 2
            p.drawString(x_pos, y, content)
            p.setFont("DejaVuSans", 12)  # возвращаем обычный шрифт
        else:
            # Обычная строка
            # Простая обработка переноса строк, если строка слишком длинная
            max_width = width - left_margin - right_margin
            text_width = p.stringWidth(line, p._fontname, p._fontsize)
            if text_width > max_width:
                # Разбиваем на слова и переносим
                words = line.split()
                current_line = ""
                for word in words:
                    test_line = current_line + " " + word if current_line else word
                    test_width = p.stringWidth(test_line, p._fontname, p._fontsize)
                    if test_width <= max_width:
                        current_line = test_line
                    else:
                        p.drawString(left_margin, y, current_line)
                        current_line = word
                        y -= 6 * mm
                        if y < bottom_margin:
                            p.showPage()
                            y = top_margin
                            if logo_path.exists():
                                y -= 60 * mm  # если на новой странице тоже нужен логотип, сдвигаем
                            try:
                                p.setFont("DejaVuSans", 12)
                            except:
                                p.setFont("Helvetica", 12)
                if current_line:
                    p.drawString(left_margin, y, current_line)
            else:
                p.drawString(left_margin, y, line)

        y -= 6 * mm
        if y < bottom_margin:
            p.showPage()
            y = top_margin
            if logo_path.exists():
                # Вставляем логотип и на новой странице (опционально)
                p.drawImage(str(logo_path), left_margin, height - 30 * mm, width=50 * mm, height=50 * mm, preserveAspectRatio=True, mask='auto')
                y -= 60 * mm
            try:
                p.setFont("DejaVuSans", 12)
            except:
                p.setFont("Helvetica", 12)

    # Добавляем подпись внизу справа (если есть)
    if signature_path:
        try:
            img = Image.open(signature_path)
            img_w, img_h = img.size
            # Ограничиваем ширину
            max_w_pt = 60 * mm
            scale = min(max_w_pt / img_w, 1.0)
            draw_w = img_w * scale
            draw_h = img_h * scale
            x = width - left_margin - draw_w
            y_sig = bottom_margin + 10 * mm
            p.drawImage(str(signature_path), x, y_sig, width=draw_w, height=draw_h, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"Ошибка вставки подписи: {e}")

    p.save()
    buffer.seek(0)
    return buffer

def secure_unique_filename(original_name):
    ext = Path(original_name).suffix
    return f"{uuid.uuid4().hex}{ext}"