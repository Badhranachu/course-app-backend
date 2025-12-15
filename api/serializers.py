#backend/api/serializers.py


from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser, Course, Video, Enrollment


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'role']



class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'password2']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        return CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password']
        )



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
        request = self.context.get("request")

        if request is None:
            return "/static/default-thumb.png"

        return request.build_absolute_uri("/static/default-thumb.png")





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


from api.models import CourseModuleItem,StudentTest
class CourseModuleSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()
    item_id = serializers.SerializerMethodField()
    attachment_url = serializers.SerializerMethodField()

    # ⭐ Computed field, NOT model field
    is_unlocked = serializers.SerializerMethodField()

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
            "attachment_url",
            "is_unlocked",   # Now VALID
        ]

    # ---------------------------------
    # TITLE
    # ---------------------------------
    def get_title(self, obj):
        if obj.item_type == "video" and obj.video:
            return obj.video.title
        if obj.item_type == "test" and obj.test:
            return obj.test.name
        return ""

    # ---------------------------------
    # DESCRIPTION
    # ---------------------------------
    def get_description(self, obj):
        if obj.item_type == "video" and obj.video:
            return obj.video.description
        if obj.item_type == "test" and obj.test:
            return obj.test.description
        return ""

    # ---------------------------------
    # THUMBNAIL (SAFE)
    # ---------------------------------
    def get_thumbnail(self, obj):
        request = self.context.get("request")
        if request is None:
            return "/static/default-thumb.png"
        return request.build_absolute_uri("/static/default-thumb.png")

    # ---------------------------------
    # ITEM ID
    # ---------------------------------
    def get_item_id(self, obj):
        if obj.item_type == "video" and obj.video:
            return obj.video.id
        if obj.item_type == "test" and obj.test:
            return obj.test.id
        return None

    # ---------------------------------
    # ATTACHMENT URL (SAFE)
    # ---------------------------------
    def get_attachment_url(self, obj):
        if obj.item_type == "video" and obj.video and obj.video.folder_attachment:
            request = self.context.get("request")
            if request is None:
                return obj.video.folder_attachment.url
            return request.build_absolute_uri(obj.video.folder_attachment.url)
        return None

    # ---------------------------------
    # UNLOCK LOGIC HERE
    # ---------------------------------
    def get_is_unlocked(self, obj):
        user = self.context.get("user")
        unlock = StudentModuleUnlock.objects.filter(user=user, module=obj).first()
        return unlock.is_unlocked if unlock else False

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




from api.models import Certificate
class CertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = "__all__"


from api.models import StudentModuleUnlock,StudentContentProgress
class StudentModuleUnlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentModuleUnlock
        fields = ['id', 'module', 'is_unlocked', 'unlocked_at']



class StudentContentProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentContentProgress
        fields = ['id', 'module', 'is_completed', 'completed_at']
