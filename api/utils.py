from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from PyPDF2 import PdfReader, PdfWriter
import io, os
from django.conf import settings

TEMPLATE_PATH = os.path.join(
    settings.BASE_DIR,
    "api",
    "static",
    "certificates",
    "template.PDF"
)

def generate_certificate(name):

    name = name.upper().strip()   # ⭐ UPPERCASE + remove extra spaces

    # Create PDF in memory
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=landscape(A4))

    # FONT
    c.setFont("Helvetica-Bold", 34)   # slightly bigger looks better
    c.setFillColorRGB(0, 0, 0)

    # POSITION (adjust until perfect)
    x = 140
    y = 315   # ⭐ Move slightly up to reduce gap

    c.drawString(x, y, name)
    c.save()

    packet.seek(0)

    # Merge with template
    name_layer = PdfReader(packet)
    template_reader = PdfReader(open(TEMPLATE_PATH, "rb"))

    output = PdfWriter()
    page = template_reader.pages[0]
    page.merge_page(name_layer.pages[0])
    output.add_page(page)

    # Output PDF path
    output_path = os.path.join(settings.MEDIA_ROOT, f"certificate_{name}.pdf")
    with open(output_path, "wb") as f:
        output.write(f)

    return output_path
