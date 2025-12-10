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
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = ['id', 'title', 'description', 'video_url', 'thumbnail', 'created_at']

    def get_video_url(self, obj):
        request = self.context.get('request')
        if request and obj.id:
            return request.build_absolute_uri(f'/api/videos/{obj.id}/stream/')
        return None

    def get_thumbnail(self, obj):
        request = self.context.get('request')
        if request and obj.video_file:
            return request.build_absolute_uri('/static/default-thumb.png') 
        return None


def get_serializer_context(self):
    return {"request": self.request}


class CourseSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField()
    is_enrolled = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "price",
            "is_active",
            "is_enrolled",
            "created_at",
            "updated_at",
        ]

    def get_is_enrolled(self, obj):
        user = self.context.get("request").user
        if user.is_authenticated:
            return Enrollment.objects.filter(user=user, course=obj).exists()
        return False

    

class CourseListSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField()
    is_enrolled = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ["id", "title", "description", "price", "is_active", "is_enrolled"]

    def get_is_enrolled(self, obj):
        user = self.context.get("request").user
        if user.is_authenticated:
            return Enrollment.objects.filter(user=user, course=obj).exists()
        return False



class EnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = Enrollment
        fields = ['id', 'user', 'course', 'course_title', 'user_email', 'status', 'enrolled_at']
        read_only_fields = ['id', 'status', 'enrolled_at']


from api.models import CourseModuleItem
class CourseModuleSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()
    item_id = serializers.SerializerMethodField()
    attachment_url = serializers.SerializerMethodField()  # ⭐ REQUIRED

    class Meta:
        model = CourseModuleItem
        fields = [
            "id",
            "item_type",
            "title",
            "description",
            "thumbnail",
            "item_id",
            "order",
            "attachment_url",   # ⭐ ADD IN FIELDS
        ]

    def get_title(self, obj):
        if obj.item_type == "video" and obj.video:
            return obj.video.title
        if obj.item_type == "test" and obj.test:
            return obj.test.name
        return ""

    def get_description(self, obj):
        if obj.item_type == "video" and obj.video:
            return obj.video.description
        if obj.item_type == "test" and obj.test:
            return obj.test.description
        return ""

    def get_thumbnail(self, obj):
        request = self.context.get("request")
        if obj.item_type == "video" and obj.video:
            return request.build_absolute_uri("/static/default-thumb.png")
        return None

    def get_item_id(self, obj):
        if obj.item_type == "video" and obj.video:
            return obj.video.id
        if obj.item_type == "test" and obj.test:
            return obj.test.id
        return None

    # ⭐⭐ FIX FOR YOUR ERROR ⭐⭐
    def get_attachment_url(self, obj):
        if obj.item_type == "video" and obj.video and obj.video.folder_attachment:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.video.folder_attachment.url)
        return None



from api.models import Question,Test
class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = [
            "id",
            "text",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "marks",
        ]


class TestDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Test
        fields = ["id", "name", "description", "questions"]