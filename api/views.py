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

        user = authenticate(email=email, password=password)
        if not user:
            return Response({"error": "Invalid credentials"}, status=401)

        token, _ = UserToken.objects.get_or_create(user=user)
        token.mark_used()

        return Response({
            "token": token.token,
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role,
            }
        })

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
        course = get_object_or_404(Course, id=course_id)

        # ✅ Must be enrolled
        if not Enrollment.objects.filter(
            user=request.user,
            course=course
        ).exists():
            return Response(
                {"error": "You must enroll first"},
                status=403
            )

        modules = CourseModuleItem.objects.filter(
            course=course
        ).order_by("order")

        # ✅ Unlock first module
        first = modules.first()
        if first:
            StudentModuleUnlock.objects.get_or_create(
                user=request.user,
                module=first,
                defaults={"is_unlocked": True}
            )

        return Response([
            CourseModuleSerializer(
                module,
                context={
                    "request": request,
                    "user": request.user
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

        razorpay_client.utility.verify_payment_signature(params)

        course = get_object_or_404(Course, id=request.data.get("course_id"))

        Enrollment.objects.create(
            user=request.user,
            course=course,
            status="completed",
            razorpay_order_id=params["razorpay_order_id"],
            razorpay_payment_id=params["razorpay_payment_id"],
        )

        return Response({"message": "Enrollment successful"})

# ============================================================
# VIDEO STREAM
# ============================================================

class StreamVideoAPIView(APIView):
    authentication_classes = [UserTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, video_id):
        video = get_object_or_404(Video, id=video_id)

        # 🔒 ENROLLMENT CHECK (VERY IMPORTANT)
        is_enrolled = Enrollment.objects.filter(
            user=request.user,
            course=video.course,
            status="completed"
        ).exists()

        if not is_enrolled:
            return Response(
                {"error": "You are not enrolled in this course"},
                status=403
            )

        video_path = video.video_file.path
        file_size = os.path.getsize(video_path)
        range_header = request.headers.get("Range")

        # ===============================
        # PARTIAL CONTENT (VIDEO SEEKING)
        # ===============================
        if range_header:
            start, end = range_header.replace("bytes=", "").split("-")
            start = int(start)
            end = int(end) if end else file_size - 1

            with open(video_path, "rb") as f:
                f.seek(start)
                data = f.read(end - start + 1)

            response = HttpResponse(data, status=206)
            response["Content-Type"] = "video/mp4"
            response["Accept-Ranges"] = "bytes"
            response["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            response["Content-Length"] = str(end - start + 1)
            response["Cache-Control"] = "no-store"
            return response

        # ===============================
        # FULL STREAM
        # ===============================
        response = FileResponse(open(video_path, "rb"), content_type="video/mp4")
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
        passed_attempt_exists = False

        previous_attempts = StudentTest.objects.filter(
            user=request.user,
            test=test
        )

        for attempt in previous_attempts:
            if attempt.total_marks > 0 and attempt.score >= (attempt.total_marks / 2):
                passed_attempt_exists = True
                break

        if passed_attempt_exists:
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
            status="completed"
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



# def build_tree_structure(file_list):
#     tree = {}
#     for path in file_list:
#         parts = path.split("/")
#         current = tree
#         for p in parts:
#             if p not in current:
#                 current[p] = {}
#             current = current[p]
#     return tree


class AttachmentTreeAPIView(APIView):
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
            status="completed"
        ).exists():
            return Response(
                {"error": "You are not enrolled in this course"},
                status=403
            )

        if not video.folder_attachment:
            return Response({"tree": {}})

        zip_path = video.folder_attachment.path
        if not zip_path.endswith(".zip"):
            return Response({"tree": {}})

        with zipfile.ZipFile(zip_path, "r") as z:
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
        video = get_object_or_404(
            Video,
            id=video_id,
            course_id=course_id
        )

        # Enrollment check
        if not Enrollment.objects.filter(
            user=request.user,
            course_id=course_id,
            status="completed"
        ).exists():
            return Response(
                {"error": "You are not enrolled in this course"},
                status=403
            )

        if not video.folder_attachment:
            return Response({"content": ""})

        try:
            with zipfile.ZipFile(video.folder_attachment.path, "r") as z:
                content = z.read(file_path).decode("utf-8", errors="ignore")
        except Exception:
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
class GenerateUserCertificateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = request.user.student_profile
        name = profile.full_name.upper()

        file_path = generate_certificate(name)
        return FileResponse(open(file_path, "rb"), as_attachment=True)



import threading
import time
from django.core.mail import EmailMessage
from api.utils import generate_certificate
from django.conf import settings
from .models import Certificate, Course


def delayed_transfer_and_email(precert_id):
    time.sleep(0)

    try:
        precert = PreCertificate.objects.select_related(
            "user",
            "course"
        ).get(id=precert_id)
    except PreCertificate.DoesNotExist:
        return

    user = precert.user
    course = precert.course
    cert_path = precert.certificate_file.path

    # ✅ ALWAYS AVAILABLE NAME
    name = user.student_profile.full_name

    # Save to Certificate
    Certificate.objects.update_or_create(
        user=user,
        course=course,
        defaults={
            "github_link": precert.github_link,
            "certificate_file": precert.certificate_file.name
        }
    )

    # Send email
    email = EmailMessage(
        subject=f"Certificate for {course.title}",
        body=(
            f"Hi {name},\n\n"
            f"Your certificate for completing the course "
            f"'{course.title}' is attached.\n\n"
            f"Regards,\nBekola Technical Solutions"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )

    email.attach_file(cert_path)
    email.send(fail_silently=True)

    precert.delete()


from django.core.files import File
from api.models import PreCertificate
class SaveGithubLinkAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, course_id):
        course = get_object_or_404(Course, id=course_id)

        # 1️⃣ Enrollment check
        if not Enrollment.objects.filter(
            user=request.user,
            course=course,
            status="completed"
        ).exists():
            return Response(
                {"error": "You are not enrolled in this course"},
                status=status.HTTP_403_FORBIDDEN
            )

        # 2️⃣ BLOCK if certificate already issued
        if Certificate.objects.filter(
            user=request.user,
            course=course
        ).exists():
            return Response(
                {"error": "Certificate already generated for this course"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3️⃣ BLOCK if request already pending
        if PreCertificate.objects.filter(
            user=request.user,
            course=course
        ).exists():
            return Response(
                {"error": "Certificate request already submitted"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4️⃣ Validate GitHub link
        github_link = request.data.get("github_link")
        if not github_link:
            return Response(
                {"error": "Github link is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 5️⃣ Generate certificate
        name = request.user.student_profile.full_name
        cert_path = generate_certificate(name)

        # 6️⃣ Save PreCertificate
        with open(cert_path, "rb") as f:
            precert = PreCertificate.objects.create(
                user=request.user,
                course=course,
                github_link=github_link,
                certificate_file=File(f, os.path.basename(cert_path))
            )

        # 7️⃣ Background processing
        threading.Thread(
            target=delayed_transfer_and_email,
            args=(precert.id,),
            daemon=True
        ).start()

        return Response(
            {"message": "Github link submitted successfully. Certificate will be emailed."},
            status=status.HTTP_200_OK
        )


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



class ListUserCertificatesAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        certs = Certificate.objects.filter(user=request.user)

        return Response([
            {
                "course_id": c.course_id,
                "course_name": c.course.title,
                "github_link": c.github_link,
                "certificate_url": request.build_absolute_uri(
                    settings.MEDIA_URL + str(c.certificate_file)
                )
            }
            for c in certs if c.certificate_file
        ])




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

MAX_FORWARD_SKIP = 1800  # ✅ 30 minutes (in seconds)

class UpdateVideoProgressAPIView(APIView):
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

        # 3️⃣ Fetch videos
        videos = Video.objects.filter(course=course)

        response = []

        for video in videos:
            progress = StudentVideoProgress.objects.filter(
                user=user,
                video=video
            ).first()

            watched = progress.watched_seconds if progress else 0
            completed = progress.is_completed if progress else False

            percentage = (
                int((watched / video.duration) * 100)
                if video.duration and watched
                else 0
            )

            response.append({
                "video_id": video.id,
                "title": video.title,
                "duration": video.duration,
                "watched_seconds": watched,
                "progress_percent": percentage,
                "last_position": progress.last_position if progress else 0,
                "is_completed": completed
            })

        return Response(response)

    def post(self, request, course_id):
        user = request.user

        video_id = request.data.get("video_id")
        current_time = int(request.data.get("current_time", 0))

        # -----------------------------
        # 1️⃣ Validate course
        # -----------------------------
        course = get_object_or_404(Course, id=course_id)

        # -----------------------------
        # 2️⃣ Enrollment check
        # -----------------------------
        if not Enrollment.objects.filter(
            user=user,
            course=course,
            status="completed"
        ).exists():
            return Response(
                {"error": "You are not enrolled in this course"},
                status=status.HTTP_403_FORBIDDEN
            )

        # -----------------------------
        # 3️⃣ Validate video
        # -----------------------------
        video = get_object_or_404(
            Video,
            id=video_id,
            course=course
        )

        # -----------------------------
        # 4️⃣ Get or create progress
        # -----------------------------
        progress, _ = StudentVideoProgress.objects.get_or_create(
            user=user,
            video=video
        )

        # -----------------------------
        # 5️⃣ Progress tracking (UPDATED)
        # -----------------------------
        delta = current_time - progress.last_position

        if settings.VIDEO_PROGRESS_TEST_MODE:
            # 🔓 TEST MODE: trust time
            progress.watched_seconds = max(
                progress.watched_seconds,
                current_time
            )
        else:
            # 🔐 PRODUCTION MODE
            if 0 < delta <= MAX_FORWARD_SKIP:
                progress.watched_seconds += delta
            # delta <= 0 → backward seek → allowed but no progress
            # delta > 1800 → skip too big → ignored

        # Update last_position ONLY if forward
        if current_time > progress.last_position:
            progress.last_position = current_time

        # Cap watched time to video duration
        progress.watched_seconds = min(
            progress.watched_seconds,
            video.duration or 0
        )

        # -----------------------------
        # 6️⃣ Completion check (90%)
        # -----------------------------
        completion_threshold = int(video.duration * 0.9) if video.duration else 0

        if (
            not progress.is_completed
            and video.duration
            and progress.watched_seconds >= completion_threshold
        ):
            progress.is_completed = True
            progress.completed_at = timezone.now()

            module = CourseModuleItem.objects.filter(
                course=course,
                video=video,
                item_type="video"
            ).first()

            if module:
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

        progress.save()

        return Response({
            "video_id": video.id,
            "course_id": course.id,
            "duration": video.duration,
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

        for module in modules:
            unlocked = StudentModuleUnlock.objects.filter(
                user=user,
                module=module,
                is_unlocked=True
            ).exists()

            completed = StudentContentProgress.objects.filter(
                user=user,
                module=module,
                is_completed=True
            ).exists()

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