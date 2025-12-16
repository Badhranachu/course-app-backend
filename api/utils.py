from docx import Document
import os
from django.conf import settings

TEMPLATE_PATH = os.path.join(
    settings.BASE_DIR,
    "api",
    "static",
    "certificates",
    "template.docx"
)

def replace_in_paragraph(paragraph, replacements):
    full_text = paragraph.text
    replaced = False

    for key, value in replacements.items():
        if key in full_text:
            full_text = full_text.replace(key, value)
            replaced = True

    if replaced:
        # ⚠️ Clear runs but keep paragraph formatting
        for run in paragraph.runs:
            run.text = ""
        paragraph.add_run(full_text)

def generate_certificate(
    name,
    title="Mr. ",
    referal="WLX-TEST-001",
    date="15-09-2024",
    start_date="01-06-2024",
    end_date="01-09-2024",
):
    doc = Document(TEMPLATE_PATH)

    replacements = {
        "{{Name}}": name.upper().strip(),
        "{{tittle}}": title,   # keep same spelling as template
        "{{referal}}": referal,
        "{{date}}": date,
        "{{start_date}}": start_date,
        "{{end_date}}": end_date,
    }

    # ✅ Paragraphs
    for paragraph in doc.paragraphs:
        replace_in_paragraph(paragraph, replacements)

    # ✅ Tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    replace_in_paragraph(paragraph, replacements)

    output_path = os.path.join(
        settings.MEDIA_ROOT,
        f"certificate_{name.replace(' ', '_')}.docx"
    )

    doc.save(output_path)
    return output_path
