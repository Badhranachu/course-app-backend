from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager
)

import uuid
from django.utils import timezone
from moviepy.editor import VideoFileClip



class MediaFile(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="uploads/")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# =====================================================
# USER TOKEN
# =====================================================

class UserToken(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="auth_token"
    )
    token = models.CharField(max_length=64, unique=True, editable=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = uuid.uuid4().hex
        super().save(*args, **kwargs)

    def mark_used(self):
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at"])

    def __str__(self):
        return f"{self.user.email} → {self.token[:8]}..."


# =====================================================
# USER MANAGER
# =====================================================

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        role = extra_fields.get("role")

        if role not in ["admin", "student"]:
            raise ValueError("Role must be either 'admin' or 'student'")

        if role == "admin":
            extra_fields.setdefault("is_staff", True)
            extra_fields.setdefault("is_superuser", True)

        return self.create_user(email, password, **extra_fields)


# =====================================================
# CUSTOM USER
# =====================================================

class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (('admin', 'Admin'), ('student', 'Student'))

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["role"]

    def __str__(self):
        return f"{self.email} ({self.role})"


# =====================================================
# PROFILES
# =====================================================

class AdminProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="admin_profile")
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True)
    linkedin_url = models.URLField(blank=True,null=True)
    website_url = models.URLField(blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AdminProfile → {self.full_name}"


class StudentProfile(models.Model):
    GENDER_CHOICES = (
        ("male", "Male"),
        ("female", "Female"),
    )
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile")
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True)
    college_name = models.CharField(max_length=150, blank=True)
    course_name = models.CharField(max_length=100, blank=True)
    github_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"StudentProfile → {self.full_name}"


# =====================================================
# COURSE
# =====================================================

class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


# =====================================================
# VIDEO
# =====================================================
from moviepy.editor import VideoFileClip
import tempfile
import shutil
import os
class Video(models.Model):
    STATUS_CHOICES = (
        ("uploading", "Uploading"),
        ("processing", "Processing"),
        ("ready", "Ready"),
        ("failed", "Failed"),
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="videos")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    folder_attachment = models.FileField(
        upload_to="video_folders/",
        blank=True,
        null=True
    )
        
    video_url = models.URLField(max_length=1000, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="uploaded",
    )
    



    duration = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.course.title} → {self.title}"



# =====================================================
# ENROLLMENT
# =====================================================

# api/models.py

class Enrollment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('upi', 'UPI'),
        ('card', 'Card'),
        ('netbanking', 'Net Banking'),
        ('wallet', 'Wallet'),
        ('unknown', 'Unknown'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    enrolled_at = models.DateTimeField(auto_now_add=True)

    # ✅ NEW FIELDS
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='unknown'
    )

    razorpay_order_id = models.CharField(max_length=255, blank=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ['user', 'course']

    def __str__(self):
        try:
            name = self.user.student_profile.full_name
        except Exception:
            name = self.user.email
        return f"{name} → {self.course.title} ({self.status})"



# =====================================================
# TESTS
# =====================================================

class Test(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="tests")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Test → {self.name} ({self.course.title})"


class Question(models.Model):
    ANSWER_CHOICES = [
        ("A", "Option A"),
        ("B", "Option B"),
        ("C", "Option C"),
        ("D", "Option D"),
    ]

    test = models.ForeignKey(
        Test,
        on_delete=models.CASCADE,
        related_name="questions"
    )
    text = models.CharField(max_length=500)

    option_a = models.CharField(max_length=200)
    option_b = models.CharField(max_length=200)
    option_c = models.CharField(max_length=200)
    option_d = models.CharField(max_length=200)

    correct_answer = models.CharField(
        max_length=1,
        choices=ANSWER_CHOICES,   # ✅ DROPDOWN
    )

    marks = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Question → {self.text[:40]}..."



# =====================================================
# MODULE ITEM
# =====================================================

class CourseModuleItem(models.Model):
    ITEM_TYPES = [("video", "Video"), ("test", "Test")]

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="modules"
    )
    item_type = models.CharField(max_length=10, choices=ITEM_TYPES)
    video = models.ForeignKey(Video, null=True, blank=True, on_delete=models.CASCADE)
    test = models.ForeignKey(Test, null=True, blank=True, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["order"]
        unique_together = ("course", "order")  # ✅ IMPORTANT

    def clean(self):
        if self.item_type == "video" and not self.video:
            raise ValidationError("Video must be set")
        if self.item_type == "test" and not self.test:
            raise ValidationError("Test must be set")

    def __str__(self):
        return f"{self.course.title} → {self.item_type} #{self.order}"

# =====================================================
# STUDENT TEST + ANSWERS
# =====================================================

class StudentTest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    total_marks = models.IntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} → {self.test.name} ({self.score}/{self.total_marks})"


class StudentAnswer(models.Model):
    student_test = models.ForeignKey(StudentTest, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.CharField(max_length=1)
    is_correct = models.BooleanField(default=False)
    marks_awarded = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Answer → {self.selected_answer} ({'✔' if self.is_correct else '✘'})"


# =====================================================
# CERTIFICATES
# =====================================================

class Certificate(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    reference_number = models.CharField(max_length=50, null=True, blank=True)  # ✅ NEW
    certificate_file = models.FileField(upload_to="certificates/", null=True, blank=True)
    github_link = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "course")

    def __str__(self):
        try:
            name = self.user.student_profile.full_name
        except Exception:
            name = self.user.email
        return f"Certificate → {name} | {self.course.title}"


class PreCertificate(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    reference_number = models.CharField(max_length=50, null=True, blank=True)  # ✅ NEW
    certificate_file = models.FileField(upload_to="pre_certificates/", null=True, blank=True)
    github_link = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "course")

    def __str__(self):
        return f"PreCertificate → {self.user.email} | {self.course.title}"


# =====================================================
# PROGRESS & UNLOCKS
# =====================================================

class StudentContentProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    module = models.ForeignKey(CourseModuleItem, on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'module')

    def __str__(self):
        return f"{self.user.email} → Module #{self.module.order} ({'done' if self.is_completed else 'pending'})"


class StudentVideoProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    video = models.ForeignKey(Video, on_delete=models.CASCADE)

    watched_seconds = models.PositiveIntegerField(default=0)
    last_position = models.PositiveIntegerField(default=0)

    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "video")



class StudentModuleUnlock(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    module = models.ForeignKey(CourseModuleItem, on_delete=models.CASCADE)
    is_unlocked = models.BooleanField(default=False)
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'module')

    def __str__(self):
        return f"{self.user.email} → Module #{self.module.order} (unlocked)"



class EmailOTP(models.Model):
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(minutes=5)
    


class CertificateSequence(models.Model):
    last_number = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Last Ref No: {self.last_number}"
    


class GrowWithUsLead(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("contacted", "Contacted"),
    ]

    full_name = models.CharField(max_length=200, unique=True)
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.status})"
    


class Announcement(models.Model):
    TYPE_CHOICES = (
        ("draft", "Draft"),
        ("scheduled", "Scheduled"),
        ("direct", "Direct"),
    )

    subject = models.CharField(max_length=200)
    message = models.TextField()

    announcement_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default="draft"
    )

    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Required if type is scheduled"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="announcements"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    is_active = models.BooleanField(default=True)

    def is_visible(self):
        """
        Determines whether students can see this announcement
        """
        if not self.is_active:
            return False

        if self.announcement_type == "direct":
            return True

        if self.announcement_type == "scheduled":
            return self.scheduled_at and self.scheduled_at <= timezone.now()

        return False  # draft

    def __str__(self):
        return f"{self.subject} ({self.announcement_type})"
    



class SupportTicket(models.Model):

    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("closed", "Closed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="support_tickets"
    )

    subject = models.CharField(max_length=255)
    message = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="open"
    )

    admin_note = models.TextField(
        blank=True,
        help_text="Internal note (admin only)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.subject} ({self.status})"