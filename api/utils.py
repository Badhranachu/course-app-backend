# api/utils.py


import os
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

import reportlab
from api.models import CertificateSequence
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from textwrap import wrap
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY\

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
FONT_DIR = os.path.join(settings.BASE_DIR, "api", "static", "fonts")

pdfmetrics.registerFont(
    TTFont("TimesNewRoman", os.path.join(FONT_DIR, "times.ttf"))
)

pdfmetrics.registerFont(
    TTFont("TimesNewRoman-Bold", os.path.join(FONT_DIR, "timesbd.ttf"))
)


def draw_justified_paragraph(canvas, text, x, y, width, leading=18):
    style = ParagraphStyle(
        name="Justified",
        fontName="Times-Roman",
        fontSize=13,
        leading=leading,
        alignment=TA_JUSTIFY
    )

    para = Paragraph(text, style)
    w, h = para.wrap(width, 1000)
    para.drawOn(canvas, x, y - h)
    return y - h



# =====================================================
# MAIN CERTIFICATE GENERATOR
# =====================================================
def generate_certificate(*, user, course):

    # ===============================
    # STUDENT DETAILS
    # ===============================
    try:
        profile = user.student_profile
        name = profile.full_name.strip().title()   # ✅ Capitalize each word
        title = "Mr. " if profile.gender == "male" else "Ms. "
    except:
        name = user.email.split("@")[0].title()
        title = "Mr. "

    # ===============================
    # ENROLLMENT DATES
    # ===============================
    enrollment = Enrollment.objects.get(user=user, course=course)
    start_date = enrollment.enrolled_at.date()
    end_date = start_date + timedelta(days=30)

    # ===============================
    # DATE + REF NUMBER
    # ===============================
    today = timezone.now().strftime("%d %B %Y")

    seq, _ = CertificateSequence.objects.get_or_create(id=1)
    seq.last_number += 1
    seq.save()

    ref_no = f"NEX/INT/2025/{str(seq.last_number).zfill(2)}"

    # ===============================
    # OUTPUT PATH
    # ===============================
    output_dir = os.path.join(settings.MEDIA_ROOT, "certificates")
    os.makedirs(output_dir, exist_ok=True)

    safe_ref = ref_no.replace("/", "-")

    pdf_path = os.path.join(
        output_dir,
        f"{safe_ref}.pdf"
    )


    # ===============================
    # CREATE PDF
    # ===============================
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    # ===============================
    # BACKGROUND TEMPLATE
    # ===============================
    bg_path = os.path.join(
        settings.BASE_DIR,
        "api",
        "static",
        "certificates",
        "template.jpg"
    )
    if os.path.exists(bg_path):
        c.drawImage(bg_path, 0, 0, width=width, height=height)

    # ===============================
    # MARGINS (NARROWER PARAGRAPH)
    # ===============================
    left_margin = 90
    right_margin = 90
    content_width = width - left_margin - right_margin

    # ===============================
    # HEADER (MOVED DOWN ~10%)
    # ===============================
    header_y = height - 210
    c.setFont("TimesNewRoman", 13)

    # Date (left aligned with paragraph)
    c.drawString(
        left_margin,
        header_y,
        f"Date: {today}"
    )

    # Ref (right aligned with paragraph)
    c.drawRightString(
        left_margin + content_width,
        header_y,
        f"Ref: {ref_no}"
    )

    # ===============================
    # TITLE (SIZE 14)
    # ===============================
    c.setFont("TimesNewRoman-Bold", 14)
    c.drawCentredString(
        width / 2,
        height - 280,
        "TO WHOMSOEVER IT MAY CONCERN"
    )

    # ===============================
    # BODY TEXT (MOVED DOWN ~10%)
    # ===============================
    cursor_y = height - 320

    para1 = (
        f"This is to certify that "
        f"<b>{title}{name}</b> has successfully completed "
        f"his internship program in <b>{course.title}</b> from "
        f"<b>{start_date.strftime('%d %B %Y')}</b> to "
        f"<b>{end_date.strftime('%d %B %Y')}</b> at Nexston."
    )

    cursor_y = draw_justified_paragraph(
        c, para1, left_margin, cursor_y, content_width
    )

    para2 = (
        "During the internship period, we found him to be extremely inquisitive, "
        "hardworking, and disciplined. He demonstrated strong interest and curiosity "
        "in understanding the functions of our core development process and consistently "
        "put in dedicated effort. He showed willingness to dive deep into both backend "
        "and frontend concepts to strengthen his practical understanding."
    )

    cursor_y = draw_justified_paragraph(
        c, para2, left_margin, cursor_y - 24, content_width
    )

    para3 = (
        "We appreciate his enthusiasm and commitment throughout the internship "
        "and wish him every success in his future endeavors."
    )

    cursor_y = draw_justified_paragraph(
        c, para3, left_margin, cursor_y - 24, content_width
    )

    # ===============================
    # FINALIZE
    # ===============================
    c.showPage()
    c.save()

    return pdf_path, ref_no

from django.core.mail import send_mail

def send_otp_email(email: str, otp: str):
    """
    Sends OTP email to user.
    """

    subject = "Your OTP Verification Code"
    message = (
        f"Dear User,\n\n"
        f"Your One-Time Password (OTP) is: {otp}\n\n"
        f"This OTP is valid for 5 minutes.\n"
        f"Please do not share this OTP with anyone.\n\n"
        f"Regards,\n"
        f"Nexston Team"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=False,
    )





# api/utils.py

import os
from datetime import timedelta
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.core.files.storage import default_storage

from api.models import (
    PreCertificate,
    Certificate,
    Enrollment,
    StudentProfile
)
import logging

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

from api.models import PreCertificate
def delayed_transfer_and_email(precert_id):
    """
    Safe to retry multiple times.
    Sends mail ONLY after 30 days from PAYMENT DATE.
    """

    try:
        precert = PreCertificate.objects.select_related(
            "user", "course"
        ).get(id=precert_id)
    except PreCertificate.DoesNotExist:
        return

    user = precert.user
    course = precert.course

    # ---------- CHECK ENROLLMENT ----------
    try:
        enrollment = Enrollment.objects.get(
            user=user,
            course=course,
            status="completed"  # ✅ IMPORTANT
        )
    except Enrollment.DoesNotExist:
        logger.info(f"No completed enrollment: {user.email}")
        return

    # ---------- PAYMENT DATE CHECK ----------
    if not enrollment.payment_date:
        logger.warning(f"Payment date missing: {user.email}")
        return

    # 🔁 CHANGE TO days=30 IN PRODUCTION
    eligible_at = enrollment.payment_date + timedelta(minutes=2)

    if timezone.now() < eligible_at:
        logger.info(f"Not eligible yet: {user.email}")
        return

    old_path = precert.certificate_file.name
    filename = os.path.basename(old_path)

    # ---------- SEND EMAIL ----------
    try:
        name = (
            user.student_profile.full_name
            if hasattr(user, "student_profile")
            else user.email.split("@")[0]
        )
        ref_no = precert.reference_number
        email = EmailMessage(
            subject=f"Certificate for {course.title}",
            body=(
            f"Hi {name},\n\n"
            f"Your internship certificate is attached.\n\n"
            f"Reference Number: {ref_no}\n\n"   # ✅ INCLUDED
            f"Regards,\n"
            f"Team Nexston"
        ),

            to=[user.email],
        )

        with default_storage.open(old_path, "rb") as f:
            email.attach(filename, f.read(), "application/pdf")

        email.send(fail_silently=False)
        logger.info(f"Email sent: {user.email}")

    except Exception:
        logger.exception("Email failed. Will retry.")
        return  # ❌ DO NOT MOVE FILE

    # ---------- MOVE FILE ----------
    try:
        new_path = f"certificates/{filename}"

        with default_storage.open(old_path, "rb") as f:
            default_storage.save(new_path, ContentFile(f.read()))

        default_storage.delete(old_path)

        Certificate.objects.update_or_create(
            user=user,
            course=course,
            defaults={
                "github_link": precert.github_link,
                "certificate_file": new_path,
                "reference_number": precert.reference_number,  # ✅ FINAL SAVE
            },
        )

        precert.delete()
        logger.info(f"Certificate finalized: {user.email}")

    except Exception:
        logger.exception("File move failed AFTER email")