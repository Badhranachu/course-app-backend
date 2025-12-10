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

from .models import (
    User, Course, Video, Enrollment,
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

@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def signup(request):
    serializer = UserSignupSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }, status=201)

    errors = serializer.errors
    if "email" in errors:
        return Response({"error": errors["email"][0]}, status=400)
    if "username" in errors:
        return Response({"error": errors["username"][0]}, status=400)
    if "password" in errors:
        return Response({"error": errors["password"][0]}, status=400)

    return Response({"error": "Signup failed"}, status=400)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def login(request):
    email = request.data.get("email")
    password = request.data.get("password")

    user = authenticate(request, email=email, password=password)
    if not user:
        if User.objects.filter(email=email).exists():
            return Response({"error": "Incorrect password"}, status=401)
        return Response({"error": "No account found with this email"}, status=401)

    refresh = RefreshToken.for_user(user)
    return Response({
        "user": UserSerializer(user).data,
        "access": str(refresh.access_token),
        "refresh": str(refresh)
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_user(request):
    return Response(UserSerializer(request.user).data)


# ------------------------------------------------------------
# COURSE CRUD
# ------------------------------------------------------------

class CourseListCreateView(generics.ListCreateAPIView):
    queryset = Course.objects.all()

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        return CourseListSerializer if self.request.method == "GET" else CourseSerializer

    def get_serializer_context(self):
        return {"request": self.request}


class CourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def get_serializer_context(self):
        return {"request": self.request}


# ------------------------------------------------------------
# COURSE MODULES
# ------------------------------------------------------------

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def course_modules(request, course_id):
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response({"error": "Course not found"}, status=404)

    if not Enrollment.objects.filter(user=request.user, course=course).exists():
        return Response({"error": "You must enroll first"}, status=403)

    modules = CourseModuleItem.objects.filter(course=course).order_by("order")
    serializer = CourseModuleSerializer(modules, many=True, context={"request": request})
    return Response(serializer.data)


# ------------------------------------------------------------
# PAYMENT
# ------------------------------------------------------------

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def create_payment_order(request):
    course_id = request.data.get("course_id")

    if not course_id:
        return Response({"error": "course_id required"}, status=400)

    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response({"error": "Course not found"}, status=404)

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


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def verify_payment(request):
    razorpay_order_id = request.data.get("razorpay_order_id")
    razorpay_payment_id = request.data.get("razorpay_payment_id")
    razorpay_signature = request.data.get("razorpay_signature")
    course_id = request.data.get("course_id")

    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response({"error": "Course not found"}, status=404)

    params = {
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": razorpay_payment_id,
        "razorpay_signature": razorpay_signature
    }

    razorpay_client.utility.verify_payment_signature(params)

    enrollment = Enrollment.objects.create(
        user=request.user,
        course=course,
        status="completed",
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
    )

    return Response({"message": "Enrollment successful"})


# ------------------------------------------------------------
# VIDEO STREAM
# ------------------------------------------------------------

@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def stream_video(request, video_id):
    try:
        video = Video.objects.get(id=video_id)
        video_path = video.video_file.path
    except Video.DoesNotExist:
        raise Http404("Video not found")

    file_size = os.path.getsize(video_path)
    range_header = request.headers.get("Range")

    if range_header:
        start, end = range_header.replace("bytes=", "").split("-")
        start = int(start)
        end = int(end) if end else file_size - 1
        chunk_size = end - start + 1

        with open(video_path, "rb") as f:
            f.seek(start)
            data = f.read(chunk_size)

        response = HttpResponse(data, status=206, content_type="video/mp4")
        response["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        response["Accept-Ranges"] = "bytes"
        response["Content-Length"] = str(chunk_size)
        return response

    return FileResponse(open(video_path, "rb"), content_type="video/mp4")


# ------------------------------------------------------------
# TEST SYSTEM
# ------------------------------------------------------------

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_test(request, test_id):
    try:
        test = Test.objects.get(id=test_id)
    except Test.DoesNotExist:
        return Response({"error": "Test not found"}, status=404)

    attempt = StudentTest.objects.filter(user=request.user, test=test).first()
    serializer = TestDetailSerializer(test)

    return Response({
        "attempted": attempt is not None,
        "score": attempt.score if attempt else None,
        "total_marks": attempt.total_marks if attempt else None,
        "test": serializer.data
    })


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def submit_test(request, test_id):
    try:
        test = Test.objects.get(id=test_id)
    except Test.DoesNotExist:
        return Response({"error": "Test not found"}, status=404)

    if StudentTest.objects.filter(user=request.user, test=test).exists():
        return Response({"error": "Already attempted"}, status=400)

    answers_data = request.data.get("answers", {})

    student_test = StudentTest.objects.create(user=request.user, test=test)
    score = 0
    total = 0

    for qid, selected in answers_data.items():
        question = Question.objects.filter(id=qid).first()
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

    student_test.score = score
    student_test.total_marks = total
    student_test.save()

    return Response({"message": "Submitted", "score": score, "total": total})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def course_test_history(request, course_id):
    tests = StudentTest.objects.filter(
        user=request.user,
        test__course_id=course_id
    ).order_by("-submitted_at")

    output = []

    for st in tests:
        ans_list = StudentAnswer.objects.filter(student_test=st)

        answers = []
        for ans in ans_list:
            q = ans.question
            answers.append({
                "question": q.text,
                "selected": ans.selected_answer,
                "correct": q.correct_answer,
                "is_correct": ans.is_correct,
                "marks": ans.marks_awarded,
            })

        output.append({
            "test_name": st.test.name,
            "score": st.score,
            "total": st.total_marks,
            "answers": answers
        })

    return Response(output)


# ------------------------------------------------------------
# ATTACHMENT HANDLING (ZIP FILE → TREE + CONTENT)
# ------------------------------------------------------------

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def attachment_preview(request, video_id):
    try:
        video = Video.objects.get(id=video_id)
    except Video.DoesNotExist:
        return Response({"filename": None})

    if not video.folder_attachment:
        return Response({"filename": None})

    return Response({
        "filename": os.path.basename(video.folder_attachment.name)
    })


def build_tree_structure(file_list):
    tree = {}
    for path in file_list:
        parts = path.split("/")
        current = tree
        for p in parts:
            if p not in current:
                current[p] = {}
            current = current[p]
    return tree


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def attachment_tree(request, video_id):
    try:
        video = Video.objects.get(id=video_id)
    except Video.DoesNotExist:
        return Response({"tree": {}})

    if not video.folder_attachment:
        return Response({"tree": {}})

    path = video.folder_attachment.path
    if not path.endswith(".zip"):
        return Response({"tree": {}})

    with zipfile.ZipFile(path, "r") as z:
        files = [f for f in z.namelist() if not f.endswith("/")]

    tree = build_tree_structure(files)
    return Response({"tree": tree})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def attachment_content(request, video_id, file_path):
    try:
        video = Video.objects.get(id=video_id)
    except Video.DoesNotExist:
        return Response({"content": ""})

    zip_path = video.folder_attachment.path

    with zipfile.ZipFile(zip_path, "r") as z:
        try:
            data = z.read(file_path).decode("utf-8", errors="ignore")
        except:
            data = "Unable to read file"

    return Response({"content": data})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def course_videos(request, course_id):
    """
    Returns list of videos for a course (old endpoint support).
    Your frontend still calls /courses/<id>/videos/
    """
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response({"error": "Course not found"}, status=404)

    # Must be enrolled
    if not Enrollment.objects.filter(user=request.user, course=course).exists():
        return Response({"error": "You must enroll in this course"}, status=403)

    videos = course.videos.all().order_by("id")
    serializer = VideoSerializer(videos, many=True, context={"request": request})
    return Response(serializer.data)