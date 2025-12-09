#backend/api/serializers.py


from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Course, Video, Enrollment


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'password2']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password']
        )
        return user


class VideoSerializer(serializers.ModelSerializer):
    video_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Video
        fields = ['id', 'title', 'description', 'video_url', 'order', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_video_url(self, obj):
        request = self.context.get('request')
        if request and obj.id:
            # Return streaming endpoint URL instead of direct file URL
            return request.build_absolute_uri(f'/api/videos/{obj.id}/stream/')
        return None


class CourseSerializer(serializers.ModelSerializer):
    videos = VideoSerializer(many=True, read_only=True)
    is_enrolled = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'price', 'videos', 'is_enrolled', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Enrollment.objects.filter(user=request.user, course=obj).exists()
        return False


class CourseListSerializer(serializers.ModelSerializer):
    is_enrolled = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'price', 'is_enrolled', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Enrollment.objects.filter(user=request.user, course=obj).exists()
        return False


class EnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = Enrollment
        fields = ['id', 'user', 'course', 'course_title', 'user_email', 'status', 'enrolled_at']
        read_only_fields = ['id', 'status', 'enrolled_at']

