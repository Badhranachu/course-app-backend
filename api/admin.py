#backend/api/admin.py


from django.contrib import admin
from .models import User, Course, Video, Enrollment


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'username', 'is_staff', 'created_at']
    list_filter = ['is_staff', 'created_at']
    search_fields = ['email', 'username']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'price', 'created_at']
    search_fields = ['title', 'description']


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order', 'created_at']
    list_filter = ['course', 'created_at']
    search_fields = ['title', 'description']


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'status', 'enrolled_at']
    list_filter = ['status', 'enrolled_at']
    search_fields = ['user__email', 'course__title']

