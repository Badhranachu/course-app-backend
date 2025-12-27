# backend/api/views.py

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.conf import settings
from django.http import FileResponse, HttpResponse, Http404
import razorpay
import os
import zipfile
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404


from django.contrib.auth import get_user_model
User = get_user_model()

from .models import (
    CustomUser, Course, Video, Enrollment,
    CourseModuleItem, Test,
    StudentTest, StudentAnswer, Question
)
from .serializers import (
    UserSerializer, UserSignupSerializer, CourseSerializer,
    CourseListSerializer, VideoSerializer, EnrollmentSerializer,
    CourseModuleSerializer, TestDetailSerializer
)

# ------------------------------------------------------------
# RAZORPAY CLIENT
# ------------------------------------------------------------
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

# ------------------------------------------------------------
# AUTH
# ------------------------------------------------------------
from api.models import UserToken
from api.models import UserToken

class SignupAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserSignupSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            # 🔐 Create persistent DB token
            token, _ = UserToken.objects.get_or_create(user=user)

            return Response({
                "user": UserSerializer(user).data,
                "token": token.token   # ✅ persistent token
            }, status=status.HTTP_201_CREATED)

        return Response(
            {"errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"error": "Email and password required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ normalize email
        email = email.strip().lower()

        user = authenticate(
            request=request,
            username=email,   # email is USERNAME_FIELD
            password=password
        )

        if not user:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response(
                {"error": "Account is disabled"},
                status=status.HTTP_403_FORBIDDEN
            )

        token, _ = UserToken.objects.get_or_create(user=user)
        token.mark_used()

        # 🔹 Name handling (safe)
        name = None
        if user.role == "student" and hasattr(user, "student_profile"):
            name = user.student_profile.full_name
        elif user.role == "admin" and hasattr(user, "admin_profile"):
            name = user.admin_profile.full_name

        return Response({
            "token": token.token,
            "user": {
                "id": user.id,
                "email": user.email,  # already stored lowercase
                "role": user.role,
                "name": name,
            }
        })

from api.models import EmailOTP
import random
from api.utils import send_otp_email


class SendEmailOTPAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response({"error": "Email required"}, status=400)

        otp = str(random.randint(100000, 999999))

        obj, _ = EmailOTP.objects.update_or_create(
            email=email,
            defaults={"otp": otp, "is_verified": False}
        )

        send_otp_email(email, otp)

        return Response({"message": "OTP sent successfully"}, status=200)
    


class VerifyEmailOTPAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")

        try:
            record = EmailOTP.objects.get(email=email)

            if record.is_expired():
                return Response({"error": "OTP expired"}, status=400)

            if record.otp != otp:
                return Response({"error": "Invalid OTP"}, status=400)

            record.is_verified = True
            record.save()

            return Response({"message": "Email verified"}, status=200)

        except EmailOTP.DoesNotExist:
            return Response({"error": "OTP not found"}, status=404)
    
class GetUserAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

# ------------------------------------------------------------
# COURSE CRUD
# ------------------------------------------------------------

from rest_framework.permissions import IsAuthenticated, IsAdminUser

class CourseListCreateAPIView(APIView):
    """
    GET  → List all courses (authenticated users)
    POST → Create course (admin only)
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    def get(self, request):
        courses = Course.objects.all()
        serializer = CourseListSerializer(
            courses,
            many=True,
            context={"request": request}
        )
        return Response(serializer.data)

    def post(self, request):
        serializer = CourseSerializer(
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from api.authentication import UserTokenAuthentication

class CourseDetailAPIView(APIView):
    """
    GET    → Retrieve course (authenticated users)
    PATCH  → Update course (admin only)
    DELETE → Delete course (admin only)
    """

    authentication_classes = [UserTokenAuthentication]

    def get_permissions(self):
        # 🔐 ALL methods require authentication
        if self.request.method in ["PATCH", "DELETE"]:
            return [IsAuthenticated(), permissions.IsAdminUser()]
        return [IsAuthenticated()]

    def get(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        serializer = CourseSerializer(course, context={"request": request})
        return Response(serializer.data)

    def patch(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        serializer = CourseSerializer(
            course,
            data=request.data,
            partial=True,
            context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        course.delete()
        return Response(
            {"message": "Course deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )

def get_user_unlock_status(user, course):
    modules = CourseModuleItem.objects.filter(course=course).order_by("order")
    unlocked_modules = []

    last_completed = True  # First module always unlocked

    for module in modules:
        module_data = CourseModuleSerializer(module, context={"request": None}).data

        if last_completed:
            module_data["is_unlocked"] = True
        else:
            module_data["is_unlocked"] = False

        unlocked_modules.append(module_data)

        # ---------- Update last_completed for NEXT module ----------
        if module.item_type == "video":
            last_completed = True

        elif module.item_type == "test":
            attempt = StudentTest.objects.filter(
                user=user, test=module.test
            ).first()

            if attempt and attempt.score >= (attempt.total_marks / 2):
                last_completed = True
            else:
                last_completed = False

    return unlocked_modules



# ------------------------------------------------------------
# COURSE MODULES
# ------------------------------------------------------------

class CourseModulesAPIView(APIView):
    authentication_classes = [UserTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        user = request.user
        course = get_object_or_404(Course, id=course_id)

        # ✅ Correct enrollment check
        if not Enrollment.objects.filter(
            user=user,
            course=course,
            status__in=["pending", "completed"]
        ).exists():
            return Response(
                {"error": "You are not enrolled in this course"},
                status=403
            )

        modules = CourseModuleItem.objects.filter(
            course=course
        ).order_by("order")

        # ✅ Unlock first module
        first = modules.first()
        if first:
            StudentModuleUnlock.objects.get_or_create(
                user=user,
                module=first,
                defaults={"is_unlocked": True}
            )

        return Response([
            CourseModuleSerializer(
                module,
                context={
                    "request": request,
                    "user": user
                }
            ).data
            for module in modules
        ])



# ------------------------------------------------------------
# PAYMENT
# ------------------------------------------------------------

class CreatePaymentOrderAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        course = get_object_or_404(Course, id=request.data.get("course_id"))

        if Enrollment.objects.filter(user=request.user, course=course).exists():
            return Response({"error": "Already enrolled"}, status=400)

        order = razorpay_client.order.create({
            "amount": int(float(course.price) * 100),
            "currency": "INR",
            "receipt": f"user_{request.user.id}_course_{course.id}"
        })

        return Response({
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key_id": settings.RAZORPAY_KEY_ID
        })


class VerifyPaymentAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        params = {
            "razorpay_order_id": request.data.get("razorpay_order_id"),
            "razorpay_payment_id": request.data.get("razorpay_payment_id"),
            "razorpay_signature": request.data.get("razorpay_signature"),
        }

        # ✅ Verify signature
        razorpay_client.utility.verify_payment_signature(params)

        # ✅ Fetch payment details (to get method)
        payment = razorpay_client.payment.fetch(
            params["razorpay_payment_id"]
        )

        payment_method = payment.get("method", "unknown")

        course = get_object_or_404(
            Course,
            id=request.data.get("course_id")
        )

        Enrollment.objects.create(
            user=request.user,
            course=course,
            status="completed",
            razorpay_order_id=params["razorpay_order_id"],
            razorpay_payment_id=params["razorpay_payment_id"],
            payment_method=payment_method,
            payment_date=timezone.now(),  # ✅ stored here
        )

        return Response({
            "message": "Enrollment successful",
            "payment_method": payment_method
        })

# ============================================================
# VIDEO STREAM
# ============================================================

from django.http import FileResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.http import StreamingHttpResponse
from wsgiref.util import FileWrapper


class StreamVideoAPIView(APIView):
    authentication_classes = []   # ❌ no auth
    permission_classes = []       # ❌ no permission

    def get(self, request, course_id, video_id):
        video = get_object_or_404(Video, id=video_id, course_id=course_id)

        file = video.video_file.open("rb")

        response = StreamingHttpResponse(
            FileWrapper(file),
            content_type="video/mp4"
        )
        response["Accept-Ranges"] = "bytes"
        response["Cache-Control"] = "no-store"

        return response
# ============================================================
# TEST SYSTEM
# ============================================================

class CourseTestsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id, test_id=None):
        # -------------------------------
        # 1️⃣ Enrollment check
        # -------------------------------
        if not Enrollment.objects.filter(
            user=request.user,
            course_id=course_id,
            status="completed"
        ).exists():
            return Response(
                {"error": "You are not enrolled in this course"},
                status=403
            )

        # -------------------------------
        # 2️⃣ LIST ALL TESTS
        # /courses/<course_id>/tests/
        # -------------------------------
        if test_id is None:
            tests = Test.objects.filter(course_id=course_id)

            return Response([
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description
                }
                for t in tests
            ])

        # -------------------------------
        # 3️⃣ SINGLE TEST DETAIL
        # /courses/<course_id>/tests/<test_id>/
        # -------------------------------
        test = get_object_or_404(
            Test,
            id=test_id,
            course_id=course_id
        )

        attempt = StudentTest.objects.filter(
            user=request.user,
            test=test
        ).first()

        return Response({
            "attempted": bool(attempt),
            "score": attempt.score if attempt else None,
            "total_marks": attempt.total_marks if attempt else None,
            "test": TestDetailSerializer(test).data
        })

class SubmitTestAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, course_id, test_id):

        # ----------------------------------
        # 1️⃣ Validate test belongs to course
        # ----------------------------------
        test = get_object_or_404(
            Test,
            id=test_id,
            course_id=course_id
        )

        # ----------------------------------
        # 2️⃣ Enrollment check
        # ----------------------------------
        if not Enrollment.objects.filter(
            user=request.user,
            course_id=course_id,
            status="completed"
        ).exists():
            return Response(
                {"error": "You are not enrolled in this course"},
                status=status.HTTP_403_FORBIDDEN
            )

        # ----------------------------------
        # 3️⃣ Block ONLY if already PASSED
        # ----------------------------------
        previous_attempts = StudentTest.objects.filter(
            user=request.user,
            test=test
        )

        for attempt in previous_attempts:
            if attempt.total_marks > 0 and attempt.score >= (attempt.total_marks / 2):
                return Response(
                    {"error": "You have already passed this test"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # ----------------------------------
        # 4️⃣ Create new attempt
        # ----------------------------------
        student_test = StudentTest.objects.create(
            user=request.user,
            test=test
        )

        score = 0
        total = 0
        answers = request.data.get("answers", {})

        # ----------------------------------
        # 5️⃣ Evaluate answers
        # ----------------------------------
        for qid, selected in answers.items():
            question = Question.objects.filter(
                id=qid,
                test=test
            ).first()

            if not question:
                continue

            is_correct = question.correct_answer == selected
            marks = question.marks if is_correct else 0

            score += marks
            total += question.marks

            StudentAnswer.objects.create(
                student_test=student_test,
                question=question,
                selected_answer=selected,
                is_correct=is_correct,
                marks_awarded=marks
            )

        # ----------------------------------
        # 6️⃣ Save result
        # ----------------------------------
        student_test.score = score
        student_test.total_marks = total
        student_test.save()

        passed = total > 0 and score >= (total / 2)

        # ======================================================
        # 7️⃣ IF PASSED → COMPLETE THIS MODULE & UNLOCK NEXT
        # ======================================================
        if passed:
            current_module = CourseModuleItem.objects.filter(
                course_id=course_id,
                item_type="test",
                test_id=test.id   # ✅ FIX HERE
            ).first()

            if current_module:
                # mark completed
                StudentContentProgress.objects.update_or_create(
                    user=request.user,
                    module=current_module,
                    defaults={
                        "is_completed": True,
                        "completed_at": timezone.now()
                    }
                )

                # unlock next module by order
                next_module = CourseModuleItem.objects.filter(
                    course_id=course_id,
                    order__gt=current_module.order
                ).order_by("order").first()

                if next_module:
                    StudentModuleUnlock.objects.update_or_create(
                        user=request.user,
                        module=next_module,
                        defaults={"is_unlocked": True}
                    )

        # ----------------------------------
        # 8️⃣ Response
        # ----------------------------------
        return Response({
            "message": "Test submitted successfully",
            "score": score,
            "total": total,
            "passed": passed
        })
    
# ============================================================
# COURSE TEST HISTORY
# ============================================================

class TestHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id, student_test_id=None):
        # ----------------------------------
        # 1️⃣ Enrollment check (MANDATORY)
        # ----------------------------------
        if not Enrollment.objects.filter(
            user=request.user,
            course_id=course_id,
            status="completed"
        ).exists():
            return Response(
                {"error": "You are not enrolled in this course"},
                status=status.HTTP_403_FORBIDDEN
            )

        # ==================================
        # CASE 1️⃣ → NO student_test_id
        # Return ALL test attempts for course
        # ==================================
        if student_test_id is None:
            attempts = StudentTest.objects.filter(
                user=request.user,
                test__course_id=course_id
            ).order_by("-submitted_at")

            return Response([
                {
                    "id": st.id,
                    "test_id": st.test.id,
                    "test_name": st.test.name,
                    "score": st.score,
                    "total_marks": st.total_marks,
                    "passed": (
                        st.total_marks > 0
                        and st.score >= (st.total_marks / 2)
                    ),
                    "submitted_at": st.submitted_at
                }
                for st in attempts
            ])

        # ==================================
        # CASE 2️⃣ → student_test_id PRESENT
        # Return FULL DETAILS
        # ==================================
        student_test = get_object_or_404(
            StudentTest,
            id=student_test_id,
            user=request.user,
            test__course_id=course_id
        )

        answers = StudentAnswer.objects.filter(
            student_test=student_test
        )

        return Response({
            "id": student_test.id,
            "test_id": student_test.test.id,
            "test_name": student_test.test.name,
            "score": student_test.score,
            "total_marks": student_test.total_marks,
            "passed": (
                student_test.total_marks > 0
                and student_test.score >= (student_test.total_marks / 2)
            ),
            "submitted_at": student_test.submitted_at,
            "answers": [
                {
                    "question": a.question.text,
                    "selected_answer": a.selected_answer,
                    "correct_answer": a.question.correct_answer,
                    "is_correct": a.is_correct,
                    "marks": a.marks_awarded
                }
                for a in answers
            ]
        })

# ------------------------------------------------------------
# ATTACHMENT HANDLING (ZIP FILE → TREE + CONTENT)
# ------------------------------------------------------------

class AttachmentPreviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id, video_id):
        video = get_object_or_404(
            Video,
            id=video_id,
            course_id=course_id
        )

        # Enrollment check
        if not Enrollment.objects.filter(
            user=request.user,
            course_id=course_id,
            status__in=["active", "completed"]
        ).exists():
            return Response(
                {"error": "You are not enrolled in this course"},
                status=403
            )

        if not video.folder_attachment:
            return Response({"filename": None})

        return Response({
            "filename": os.path.basename(video.folder_attachment.name)
        })




import zipfile
from io import BytesIO

class AttachmentTreeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id, video_id):
        video = get_object_or_404(Video, id=video_id, course_id=course_id)

        if not Enrollment.objects.filter(
            user=request.user,
            course_id=course_id,
            status="completed"
        ).exists():
            return Response({"error": "You are not enrolled"}, status=403)

        if not video.folder_attachment:
            return Response({"tree": {}})

        if not video.folder_attachment.name.lower().endswith(".zip"):
            return Response({"tree": {}})

        # ✅ MUST OPEN FIRST (Cloudflare R2)
        with video.folder_attachment.open("rb") as f:
            zip_bytes = BytesIO(f.read())

        with zipfile.ZipFile(zip_bytes, "r") as z:
            files = [f for f in z.namelist() if not f.endswith("/")]

        tree = {}
        for f in files:
            current = tree
            for part in f.split("/"):
                current = current.setdefault(part, {})

        return Response({"tree": tree})


class AttachmentContentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id, video_id, file_path):
        video = get_object_or_404(Video, id=video_id, course_id=course_id)

        if not Enrollment.objects.filter(
            user=request.user,
            course_id=course_id,
            status="completed"
        ).exists():
            return Response({"error": "You are not enrolled"}, status=403)

        if not video.folder_attachment:
            return Response({"content": ""})

        try:
            with video.folder_attachment.open("rb") as f:
                zip_bytes = BytesIO(f.read())

            with zipfile.ZipFile(zip_bytes, "r") as z:
                content = z.read(file_path).decode("utf-8", errors="ignore")

        except Exception as e:
            content = "Unable to read file"

        return Response({"content": content})

class CourseVideosAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, course_id):
        course = get_object_or_404(Course, id=course_id)

        if not Enrollment.objects.filter(user=request.user, course=course).exists():
            return Response({"error": "You must enroll in this course"}, status=403)

        videos = course.videos.all().order_by("id")
        serializer = VideoSerializer(videos, many=True, context={"request": request})
        return Response(serializer.data)


from api.utils import generate_certificate
# class GenerateUserCertificateAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         profile = request.user.student_profile
#         name = profile.full_name.upper()

#         # 1️⃣ Generate certificate PDF (returns local path + reference)
#         file_path, reference_number = generate_certificate(name, request.user)

#         # 2️⃣ Create DB record
#         cert = Certificate.objects.create(
#             user=request.user,
#             course=profile.course,  # adjust if needed
#             reference_number=reference_number,
#         )

#         # 3️⃣ Save file to FileField (VERY IMPORTANT)
#         with open(file_path, "rb") as f:
#             cert.certificate_file.save(
#                 os.path.basename(file_path),
#                 f,
#                 save=True
#             )

#         # 4️⃣ Stream file securely from R2
#         return FileResponse(
#             cert.certificate_file.open("rb"),
#             as_attachment=True,
#             filename=f"{reference_number}.pdf",
#         )




import threading
import time
from django.core.mail import EmailMessage
from api.utils import generate_certificate
from django.conf import settings
from .models import Certificate, Course
import traceback


import os
import logging
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.files.storage import default_storage
from django.db import transaction

from api.models import (
    PreCertificate,
    Certificate,
    StudentProfile,
)
from django.core.files.base import ContentFile   # ✅ REQUIRED
from datetime import timedelta




from django.core.files import File
from api.models import PreCertificate,StudentProfile
import logging
logger = logging.getLogger(__name__)
from api.utils import delayed_transfer_and_email


class SaveGithubLinkAPIView(APIView):
    permission_classes = [IsAuthenticated]

    # ------------------------------
    # GET STATUS
    # ------------------------------
    def get(self, request, course_id):
        course = get_object_or_404(Course, id=course_id)

        cert = Certificate.objects.filter(
            user=request.user,
            course=course
        ).first()

        if cert:
            return Response({
                "completed": True,
                "github_link": cert.github_link,
                "certificate_generated": True
            }, status=200)

        precert = PreCertificate.objects.filter(
            user=request.user,
            course=course
        ).first()

        if precert:
            return Response({
                "completed": True,
                "github_link": precert.github_link,
                "certificate_generated": False
            }, status=200)

        return Response({"completed": False}, status=200)

    # ------------------------------
    # POST SUBMISSION
    # ------------------------------
    permission_classes = [IsAuthenticated]

    def post(self, request, course_id):
        course = get_object_or_404(Course, id=course_id)

        # must be completed enrollment
        try:
            enrollment = Enrollment.objects.get(
                user=request.user,
                course=course,
                status="completed"
            )
        except Enrollment.DoesNotExist:
            return Response({"error": "Not enrolled"}, status=403)

        # prevent duplicate final certificate
        if Certificate.objects.filter(
            user=request.user, course=course
        ).exists():
            return Response(
                {"error": "Certificate already generated"},
                status=400
            )

        github_link = request.data.get("github_link")
        if not github_link:
            return Response(
                {"error": "Github link required"},
                status=400
            )

        # generate certificate locally
        cert_path, ref_no = generate_certificate(
            user=request.user,
            course=course
        )

        try:
            with open(cert_path, "rb") as f:
                with transaction.atomic():
                    precert, _ = PreCertificate.objects.update_or_create(
                        user=request.user,
                        course=course,
                        defaults={
                            "github_link": github_link,
                            "reference_number": ref_no,
                            "certificate_file": File(
                                f,
                                f"{os.path.basename(cert_path)}"
                            ),
                        },
                    )
        except Exception:
            logger.exception("PreCertificate creation failed")
            return Response(
                {"error": "Failed"},
                status=500
            )

        # 🔥 NEW LOGIC: IMMEDIATE ELIGIBILITY CHECK
        from api.utils import delayed_transfer_and_email
        delayed_transfer_and_email(precert.id)

        return Response(
            {
                "message": (
                    "Github link saved. "
                    "If eligible, certificate has been emailed."
                )
            },
            status=200,
        )
    
from django.db import IntegrityError
from django.db import transaction



class GetGithubLinkAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, course_id):
        cert = Certificate.objects.filter(
            user=request.user,
            course_id=course_id
        ).first()

        return Response({
            "github_link": cert.github_link if cert else None
        })

from django.core.mail import EmailMessage

class SendCourseCertificateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, course_id):
        cert = get_object_or_404(
            Certificate,
            user=request.user,
            course_id=course_id
        )

        name = request.user.student_profile.full_name
        file_path = generate_certificate(name)

        email = EmailMessage(
            subject="Course Certificate",
            body="Certificate attached",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[request.user.email]
        )

        email.attach_file(file_path)
        email.send()

        cert.certificate_file = file_path.replace(str(settings.MEDIA_ROOT) + "/", "")
        cert.save()

        return Response({"message": "Certificate sent"})



from django.core.mail import EmailMessage       # sending email
from django.conf import settings               # for DEFAULT_FROM_EMAIL
from api.utils import generate_certificate     # certificate PDF generator
from .models import Certificate                # your model
from .models import PreCertificate


from django.urls import reverse

class ListUserCertificatesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        certs = Certificate.objects.filter(user=request.user)

        return Response([
            {
                "course_id": c.course_id,
                "course_name": c.course.title,
                "github_link": c.github_link,
                "certificate_url": request.build_absolute_uri(
                    reverse("my-certificate-download", args=[c.reference_number])
                )
            }
            for c in certs if c.certificate_file
        ])


class MyCertificateDownloadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, reference_number):
        try:
            cert = Certificate.objects.get(
                reference_number=reference_number,
                user=request.user
            )
        except Certificate.DoesNotExist:
            raise Http404("Certificate not found")

        return FileResponse(
            cert.certificate_file.open("rb"),
            as_attachment=True,
            filename=f"{reference_number}.pdf",
        )
    
from api.models import StudentContentProgress,StudentModuleUnlock
class CompleteVideoAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, module_id):
        module = get_object_or_404(
            CourseModuleItem,
            id=module_id,
            item_type="video"
        )

        StudentContentProgress.objects.update_or_create(
            user=request.user,
            module=module,
            defaults={"is_completed": True}
        )

        next_module = CourseModuleItem.objects.filter(
            course=module.course,
            order=module.order + 1
        ).first()

        if next_module:
            StudentModuleUnlock.objects.update_or_create(
                user=request.user,
                module=next_module,
                defaults={"is_unlocked": True}
            )

        return Response({"message": "Video completed"})




from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from api.models import (
    Video,
    CourseModuleItem,
    StudentVideoProgress,
    StudentContentProgress,
    StudentModuleUnlock
)
from django.conf import settings

from moviepy.editor import VideoFileClip
import tempfile
import shutil
from moviepy.editor import VideoFileClip


def ensure_video_duration(video):
    """
    Calculate and save video duration ONLY if missing.
    Windows-safe (no file lock issue).
    """
    if video.duration:
        return video.duration

    if not video.video_file:
        return 0

    tmp_path = None

    try:
        # 1️⃣ Create temp file path (not locked)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp_path = tmp.name
            with video.video_file.open("rb") as src:
                shutil.copyfileobj(src, tmp)

        # 2️⃣ Now ffmpeg/moviepy can read it
        clip = VideoFileClip(tmp_path)
        duration = int(clip.duration)
        clip.close()

        # 3️⃣ Save duration
        video.duration = duration
        video.save(update_fields=["duration"])

        return duration

    except Exception:
        import traceback
        traceback.print_exc()
        return 0

    finally:
        # 4️⃣ Cleanup temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    
MAX_FORWARD_SKIP = 1800  # ✅ 30 minutes (in seconds)

class UpdateVideoProgressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    # ==============================
    # GET → FETCH PROGRESS
    # ==============================
    def get(self, request, course_id):
        user = request.user
        course = get_object_or_404(Course, id=course_id)

        if not Enrollment.objects.filter(
            user=user, course=course
        ).exists():
            return Response({"error": "Not enrolled"}, status=403)

        videos = Video.objects.filter(course=course)
        response = []

        for video in videos:
            # ✅ ENSURE DURATION EVEN IN GET
            duration = ensure_video_duration(video)

            progress = StudentVideoProgress.objects.filter(
                user=user, video=video
            ).first()

            watched = progress.watched_seconds if progress else 0
            completed = progress.is_completed if progress else False

            percentage = (
                int((watched / duration) * 100)
                if duration > 0
                else 0
            )

            response.append({
                "video_id": video.id,
                "title": video.title,
                "duration": duration,
                "watched_seconds": watched,
                "progress_percent": percentage,
                "last_position": progress.last_position if progress else 0,
                "is_completed": completed,
            })

        return Response(response)

    # ==============================
    # POST → UPDATE PROGRESS
    # ==============================
    def post(self, request, course_id):
        user = request.user

        video_id = request.data.get("video_id")
        current_time = request.data.get("current_time")

        # 🔒 HARD SAFETY DEFAULT
        current_time = int(current_time) if current_time is not None else 0

        course = get_object_or_404(Course, id=course_id)

        if not Enrollment.objects.filter(
            user=user,
            course=course,
            status__in=["pending", "completed"]
        ).exists():
            return Response({"error": "Not enrolled"}, status=403)

        video = get_object_or_404(Video, id=video_id, course=course)

        module = get_object_or_404(
            CourseModuleItem,
            course=course,
            video=video,
            item_type="video"
        )

        progress, _ = StudentVideoProgress.objects.get_or_create(
            user=user,
            video=video,
            defaults={
                "watched_seconds": 0,
                "last_position": 0,
                "is_completed": False,
            }
        )

        # 🔥 HARD NULL SAFETY (CRITICAL)
        if progress.watched_seconds is None:
            progress.watched_seconds = 0

        if progress.last_position is None:
            progress.last_position = 0

        # ==============================
        # 🔒 SAFE SYNC (NO NULLS)
        # ==============================
        duration = ensure_video_duration(video)

        if duration and current_time >= int(duration * 0.9):
            progress.watched_seconds = duration
            progress.last_position = duration
        else:
            capped_time = min(current_time, duration)
            progress.last_position = max(progress.last_position or 0, capped_time)
            progress.watched_seconds = max(progress.watched_seconds or 0, capped_time)

        # ==============================
        # ✅ COMPLETION CHECK (90%)
        # ==============================
        # ==============================
        # ✅ COMPLETION CHECK (>= 90%)
        # ==============================
        if duration:
            watched_percent = (progress.watched_seconds / duration) * 100
        else:
            watched_percent = 0

        if not progress.is_completed and watched_percent >= 90:
            progress.is_completed = True
            progress.completed_at = timezone.now()

            # 🔒 force to full duration
            progress.last_position = duration
            progress.watched_seconds = duration

            StudentContentProgress.objects.update_or_create(
                user=user,
                module=module,
                defaults={
                    "is_completed": True,
                    "completed_at": timezone.now()
                }
            )

            next_module = CourseModuleItem.objects.filter(
                course=course,
                order__gt=module.order
            ).order_by("order").first()

            if next_module:
                StudentModuleUnlock.objects.update_or_create(
                    user=user,
                    module=next_module,
                    defaults={"is_unlocked": True}
                )
            else:
                Enrollment.objects.filter(
                    user=user,
                    course=course
                ).update(status="completed")

        progress.save()

        return Response({
            "video_id": video.id,
            "watched_seconds": progress.watched_seconds,
            "last_position": progress.last_position,
            "is_completed": progress.is_completed
        })


class CourseModuleProgressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        user = request.user

        # 1️⃣ Validate course
        course = get_object_or_404(Course, id=course_id)

        # 2️⃣ Enrollment check
        if not Enrollment.objects.filter(
            user=user,
            course=course,
            status="completed"
        ).exists():
            return Response(
                {"error": "You are not enrolled in this course"},
                status=403
            )

        # 3️⃣ Fetch all modules in order
        modules = CourseModuleItem.objects.filter(
            course=course
        ).order_by("order")

        response = []
        previous_completed = False

        for index, module in enumerate(modules):
            # 🔓 FIRST MODULE ALWAYS UNLOCKED
            if index == 0:
                unlocked = True
            else:
                unlocked = previous_completed

            # ✅ CHECK COMPLETION
            if module.item_type == "video" and module.video:
                completed = StudentVideoProgress.objects.filter(
                    user=user,
                    video=module.video,
                    is_completed=True
                ).exists()
            else:
                completed = StudentContentProgress.objects.filter(
                    user=user,
                    module=module,
                    is_completed=True
                ).exists()

            # 🔥 UPDATE previous_completed for next iteration
            previous_completed = completed

            item_data = {
                "module_id": module.id,
                "order": module.order,
                "item_type": module.item_type,
                "is_unlocked": unlocked,
                "is_completed": completed,
            }

            if module.item_type == "video" and module.video:
                item_data.update({
                    "video_id": module.video.id,
                    "title": module.video.title,
                    "duration": module.video.duration
                })

            if module.item_type == "test" and module.test:
                item_data.update({
                    "test_id": module.test.id,
                    "title": module.test.name
                })

            response.append(item_data)


        return Response({
            "course_id": course.id,
            "course_title": course.title,
            "modules": response
        })
    

from rest_framework.permissions import AllowAny
class CertificateCheckAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        reference_number = request.data.get("reference_number")

        if not reference_number:
            return Response(
                {"error": "Reference number is required"},
                status=400
            )

        try:
            cert = Certificate.objects.select_related(
                "user", "course"
            ).get(reference_number=reference_number)
        except Certificate.DoesNotExist:
            return Response(
                {"error": "Certificate not found"},
                status=404
            )

        # Safe student name
        try:
            name = cert.user.student_profile.full_name
        except Exception:
            name = cert.user.email

        # 🔥 Dynamic base URL (local + production safe)
        base_url = request.build_absolute_uri("/").rstrip("/")

        return Response(
            {
                "status": "valid",
                "reference_number": cert.reference_number,
                "student_name": name,
                "course": cert.course.title,
                "issued_on": cert.created_at.strftime("%d %B %Y"),
                "certificate_url": (
                    f"{base_url}/api/certificate/download/"
                    f"{cert.reference_number}/"
                ),
            },
            status=200
        )
    

from django.shortcuts import redirect

class CertificateDownloadAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, reference_number):
        try:
            cert = Certificate.objects.get(reference_number=reference_number)
        except Certificate.DoesNotExist:
            raise Http404("Certificate not found")

        if not cert.certificate_file:
            raise Http404("Certificate file not available")

        # ✅ storage-safe (works for local + R2)
        file = cert.certificate_file
        file.open("rb")

        response = FileResponse(
            file,
            content_type="application/pdf"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{reference_number}.pdf"'
        )
        return response

    
from django.conf import settings
from django.core.mail import send_mail
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import GrowWithUsLead
from api.models import CustomUser
class GrowWithUsView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):

        full_name = request.data.get("full_name")
        phone = request.data.get("phone")
        email = request.data.get("email")

        try:
            # 1️⃣ Try to create lead
            lead, created = GrowWithUsLead.objects.get_or_create(
                email=email,          # PRIMARY uniqueness anchor
                defaults={
                    "full_name": full_name,
                    "phone": phone,
                }
            )

        except IntegrityError:
            # Safety net (rare race condition)
            return Response(
                {
                    "message": (
                        "Your details are already present in our system. "
                        "Our team will contact you shortly."
                    )
                },
                status=200
            )

        # 2️⃣ If already exists → friendly message
        if not created:
            return Response(
                {
                    "message": (
                        "Your details are already present in our system. "
                        "Our team will contact you shortly."
                    )
                },
                status=200
            )

        # 3️⃣ Send email ONLY if newly created
        admin_emails = list(
            CustomUser.objects.filter(
                role="admin",
                is_active=True
            ).values_list("email", flat=True)
        )

        if admin_emails:
            send_mail(
                subject="New Grow With Us Contact Request",
                message=f"""
                A new user has submitted the Grow With Us form.

                Name: {lead.full_name}
                Phone: {lead.phone}
                Email: {lead.email}

                Status: {lead.status}
                Submitted At: {lead.submitted_at}
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=admin_emails,
                fail_silently=True,
            )

        return Response(
            {"message": "Thank you! Our team will contact you soon."},
            status=201
        )
    

from api.models import Announcement
from api.serializers import AnnouncementSerializer
class AnnouncementListAPIView(APIView):
    permission_classes = []  # students & public users can access

    def get(self, request):
        now = timezone.now()

        announcements = Announcement.objects.filter(
            is_active=True
        ).filter(
            # Direct announcements
            announcement_type="direct"
        ) | Announcement.objects.filter(
            # Scheduled announcements whose time has passed
            announcement_type="scheduled",
            scheduled_at__lte=now
        )

        announcements = announcements.order_by("-created_at")

        serializer = AnnouncementSerializer(announcements, many=True)
        return Response(serializer.data)
    

from api.permissions import IsStudent
from api.serializers import StudentProfileSerializer
class StudentProfileAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        """
        Get logged-in student's profile
        """
        profile = StudentProfile.objects.get(user=request.user)
        serializer = StudentProfileSerializer(profile)
        return Response(serializer.data)

    def patch(self, request):
        """
        Update logged-in student's profile (partial)
        """
        profile = StudentProfile.objects.get(user=request.user)
        serializer = StudentProfileSerializer(
            profile,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    

from api.serializers import StudentEnrollmentSerializer
class StudentEnrollmentListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        """
        Get all enrollments for logged-in student
        """
        enrollments = Enrollment.objects.filter(
            user=request.user
        ).select_related("course").order_by("-enrolled_at")

        serializer = StudentEnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)
    



from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import SupportTicket

class CreateSupportTicketAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        subject = request.data.get("subject")
        message = request.data.get("message")

        if not subject or not message:
            return Response(
                {"error": "Subject and message are required"},
                status=400
            )

        SupportTicket.objects.create(
            user=request.user,
            subject=subject,
            message=message
        )

        return Response(
            {"message": "Support ticket created successfully"},
            status=201
        )
    



class MySupportTicketsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tickets = SupportTicket.objects.filter(
            user=request.user
        ).order_by("-created_at")

        data = [
            {
                "id": t.id,
                "subject": t.subject,
                "message": t.message,
                "status": t.status,
                "admin_note": t.admin_note,
                "created_at": t.created_at,
            }
            for t in tickets
        ]

        return Response(data)




class MyCertificateDownloadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, reference_number):
        try:
            cert = Certificate.objects.get(
                reference_number=reference_number,
                user=request.user   # 🔐 security
            )
        except Certificate.DoesNotExist:
            raise Http404("Certificate not found")

        return FileResponse(
            cert.certificate_file.open("rb"),
            as_attachment=True,
            filename=f"{reference_number}.pdf",
        )