from django.contrib import admin
from django.apps import apps
from django import forms
import tempfile
import shutil
import os

from moviepy.editor import VideoFileClip

from .models import (
    Course,
    CourseModuleItem,
    SupportTicket,
    Video,
)

from api.r2 import upload_video_to_r2


# =====================================================
# VIDEO ADMIN FORM (Cloudflare R2 + Folder Attachment)
# =====================================================

class VideoAdminForm(forms.ModelForm):
    video_file = forms.FileField(
        required=False,
        help_text="Upload video only when adding or replacing"
    )

    class Meta:
        model = Video
        fields = (
            "course",
            "title",
            "description",
            "folder_attachment",
        )

    def save(self, commit=True):
        instance = super().save(commit=False)
        video_file = self.cleaned_data.get("video_file")

        # 🔹 Only upload if a NEW file is provided
        if video_file:
            import tempfile, os
            from moviepy.editor import VideoFileClip
            from api.r2 import upload_video_to_r2

            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                    tmp_path = tmp.name
                    for chunk in video_file.chunks():
                        tmp.write(chunk)

                # Upload to Cloudflare
                with open(tmp_path, "rb") as f:
                    instance.video_url = upload_video_to_r2(
                        f,
                        folder=f"course-{instance.course.id}"
                    )

                # Extract duration
                clip = VideoFileClip(tmp_path)
                instance.duration = int(clip.duration)
                clip.close()

            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)

        if commit:
            instance.save()

        return instance


# =====================================================
# VIDEO ADMIN
# =====================================================

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    form = VideoAdminForm

    list_display = (
        "id",
        "course",
        "title",
        "duration",
        "created_at",
    )

    search_fields = ("title",)
    list_filter = ("course",)

    readonly_fields = (
        "video_url",
        "duration",
        "created_at",
    )

    fields = (
        "course",
        "title",
        "description",
        "video_file",
        "video_url",
        "folder_attachment",
        "duration",
        "created_at",
    )


# =====================================================
# AUTO-REGISTER ALL OTHER MODELS
# =====================================================

app = apps.get_app_config("api")

EXCLUDE_MODELS = {
    Video,
    CourseModuleItem,
    SupportTicket,
}

for model in app.get_models():
    if model in EXCLUDE_MODELS:
        continue
    try:
        admin.site.register(model)
    except admin.sites.AlreadyRegistered:
        pass


# =====================================================
# COURSE MODULE ITEM ADMIN (CUSTOM)
# =====================================================

class CourseModuleItemAdminForm(forms.ModelForm):
    class Meta:
        model = CourseModuleItem
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        course = None

        if self.instance.pk:
            course = self.instance.course
        elif "course" in self.data:
            try:
                course = Course.objects.get(id=int(self.data.get("course")))
            except Exception:
                pass

        if course:
            used_orders = CourseModuleItem.objects.filter(
                course=course
            ).exclude(pk=self.instance.pk).values_list("order", flat=True)

            max_order = max(used_orders, default=0) + 5

            self.fields["order"].widget = forms.Select(
                choices=[
                    (i, i)
                    for i in range(1, max_order + 1)
                    if i not in used_orders
                ]
            )


@admin.register(CourseModuleItem)
class CourseModuleItemAdmin(admin.ModelAdmin):
    form = CourseModuleItemAdminForm
    list_display = ("course", "item_type", "order")
    list_filter = ("course", "item_type")
    ordering = ("course", "order")


# =====================================================
# SUPPORT TICKET ADMIN
# =====================================================

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "subject",
        "user",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("subject", "message", "user__email")
    ordering = ("-created_at",)
    readonly_fields = ("user", "created_at", "updated_at")
