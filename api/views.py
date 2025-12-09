#backend/api/views.py

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.conf import settings
from django.http import FileResponse, Http404, StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
import razorpay
import os

from .models import User, Course, Video, Enrollment
from .serializers import (
    UserSerializer, UserSignupSerializer, CourseSerializer,
    CourseListSerializer, VideoSerializer, EnrollmentSerializer
)


# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def signup(request):
    serializer = UserSignupSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login(request):
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response(
            {'error': 'Email and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(username=email, password=password)
    if user:
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        })
    return Response(
        {'error': 'Invalid credentials'},
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_user(request):
    return Response(UserSerializer(request.user).data)


class CourseListCreateView(generics.ListCreateAPIView):
    queryset = Course.objects.all()
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return CourseListSerializer
        return CourseSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class CourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def course_videos(request, course_id):
    try:
        course = Course.objects.get(id=course_id)
        enrollment = Enrollment.objects.filter(user=request.user, course=course).exists()
        
        if not enrollment:
            return Response(
                {'error': 'You must enroll in this course to access videos'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        videos = course.videos.all()
        serializer = VideoSerializer(videos, many=True, context={'request': request})
        return Response(serializer.data)
    except Course.DoesNotExist:
        return Response(
            {'error': 'Course not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_payment_order(request):
    course_id = request.data.get('course_id')
    
    if not course_id:
        return Response(
            {'error': 'course_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response(
            {'error': 'Course not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if already enrolled
    if Enrollment.objects.filter(user=request.user, course=course).exists():
        return Response(
            {'error': 'You are already enrolled in this course'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create Razorpay order
    amount = int(float(course.price) * 100)  # Convert to paise
    
    order_data = {
        'amount': amount,
        'currency': 'INR',
        'receipt': f'course_{course_id}_user_{request.user.id}',
        'notes': {
            'course_id': course_id,
            'user_id': request.user.id,
        }
    }
    
    try:
        razorpay_order = razorpay_client.order.create(data=order_data)
        return Response({
            'order_id': razorpay_order['id'],
            'amount': razorpay_order['amount'],
            'currency': razorpay_order['currency'],
            'key_id': settings.RAZORPAY_KEY_ID,
        })
    except Exception as e:
        return Response(
            {'error': f'Failed to create order: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def verify_payment(request):
    razorpay_order_id = request.data.get('razorpay_order_id')
    razorpay_payment_id = request.data.get('razorpay_payment_id')
    razorpay_signature = request.data.get('razorpay_signature')
    course_id = request.data.get('course_id')
    
    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature, course_id]):
        return Response(
            {'error': 'Missing required payment data'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response(
            {'error': 'Course not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Verify payment signature
    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }
    
    try:
        razorpay_client.utility.verify_payment_signature(params_dict)
        
        # Create enrollment
        enrollment, created = Enrollment.objects.get_or_create(
            user=request.user,
            course=course,
            defaults={
                'status': 'completed',
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
            }
        )
        
        if not created:
            return Response(
                {'error': 'Enrollment already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            'message': 'Payment verified and enrollment successful',
            'enrollment': EnrollmentSerializer(enrollment).data
        })
    except razorpay.errors.SignatureVerificationError:
        return Response(
            {'error': 'Payment verification failed'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': f'Payment verification error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def stream_video(request, video_id):
    try:
        video = Video.objects.get(id=video_id)
        
        # Check if user is enrolled in the course
        enrollment = Enrollment.objects.filter(
            user=request.user,
            course=video.course
        ).exists()
        
        if not enrollment:
            return Response(
                {'error': 'You must enroll in this course to access videos'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        video_file = video.video_file
        if not video_file or not video_file.name:
            return Response(
                {'error': 'Video file not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            file_path = video_file.path
            if not os.path.exists(file_path):
                return Response(
                    {'error': 'Video file not found on server'},
                    status=status.HTTP_404_NOT_FOUND
                )
        except ValueError:
            # FileField might not have a path if using storage backend
            file_path = None
        
        # Use FileResponse with the file object for proper handling
        file_obj = video_file.open('rb')
        response = FileResponse(file_obj, content_type='video/mp4')
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(video_file.name)}"'
        response['Accept-Ranges'] = 'bytes'
        return response
    except Video.DoesNotExist:
        return Response(
            {'error': 'Video not found'},
            status=status.HTTP_404_NOT_FOUND
        )



