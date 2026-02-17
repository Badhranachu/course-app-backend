from django.contrib import admin
from django.apps import apps
from django import forms
from django.utils import timezone

from .models import (
    Course,
    CourseModuleItem,
    SupportTicket,
    Video,
    Contactus,
)

# =====================================================
# VIDEO ADMIN FORM
# =====================================================
class VideoAdminForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = (
            "course",
            "title",
            "description",
            "folder_attachment",
        )


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
        "video_url",
        "created_at",
    )

    search_fields = ("title",)
    list_filter = ("course",)

    readonly_fields = (
        # "duration",
        "created_at",
        # "video_url",

    )

    fields = (
        "course",
        "title",
        "description",
        "video_url",
        "folder_attachment",
        "duration",
        "created_at",
    )


# =====================================================
# COURSE MODULE ITEM ADMIN
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


# =====================================================
# CONTACT US ADMIN (CUSTOM)
# =====================================================
@admin.register(Contactus)
class ContactusAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "email",
        "subject",
        "status",
        "created_at",
    )

    list_filter = ("status", "created_at")
    search_fields = ("full_name", "email", "subject")
    ordering = ("-created_at",)

    readonly_fields = (
        "full_name",
        "email",
        "subject",
        "message",
        "created_at",
        "contacted_at",
    )

    fields = (
        "full_name",
        "email",
        "subject",
        "message",
        "status",        # dropdown
        "contacted_at",
        "created_at",
    )

    def save_model(self, request, obj, form, change):
        if obj.status == "contacted" and obj.contacted_at is None:
            obj.contacted_at = timezone.now()
        super().save_model(request, obj, form, change)




from django.utils import timezone
from api.models import CoordinatorPayout,CoordinatorStudent

class CoordinatorStudentInline(admin.TabularInline):
    model = CoordinatorStudent
    extra = 0
    readonly_fields = (
        "student",
        "course",
        "email",
        "is_paid",
        "created_at",
    )
    can_delete = False


@admin.register(CoordinatorPayout)
class CoordinatorPayoutAdmin(admin.ModelAdmin):

    list_display = (
        "coordinator",
        "total_students",
        "total_amount",
        "status",
        "requested_at",
        "processed_at",
    )

    list_filter = ("status", "requested_at")

    inlines = [CoordinatorStudentInline]

    def save_model(self, request, obj, form, change):

        if change:
            previous = CoordinatorPayout.objects.get(pk=obj.pk)

            # Approve payout
            if previous.status == "pending" and obj.status == "approved":
                obj.processed_at = timezone.now()
                obj.students.update(is_paid=True)

            # Reject payout
            if previous.status == "pending" and obj.status == "rejected":
                obj.students.update(payout_reference=None)

        super().save_model(request, obj, form, change)

from api.models import CoordinatorPayout
# =====================================================
# AUTO-REGISTER ALL OTHER MODELS
# =====================================================
app = apps.get_app_config("api")
EXCLUDE_MODELS = {
    Video,
    CourseModuleItem,
    SupportTicket,
    Contactus,   # ✅ IMPORTANT FIX
    CoordinatorPayout
    
}

for model in app.get_models():
    if model in EXCLUDE_MODELS:
        continue
    try:
        admin.site.register(model)
    except admin.sites.AlreadyRegistered:
        pass
