from django.contrib import admin
from django.apps import apps
from django import forms

from .models import (
    Course,
    CourseModuleItem,
    SupportTicket,
)

# =====================================================
# AUTO-REGISTER ALL MODELS EXCEPT THOSE WITH CUSTOM ADMIN
# =====================================================

app = apps.get_app_config("api")

EXCLUDE_MODELS = {
    CourseModuleItem,   # custom admin below
    SupportTicket,      # custom admin below
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

        # Edit mode
        if self.instance.pk:
            course = self.instance.course

        # Add mode (course selected)
        elif "course" in self.data:
            try:
                course_id = int(self.data.get("course"))
                course = Course.objects.get(id=course_id)
            except Exception:
                pass

        if course:
            used_orders = CourseModuleItem.objects.filter(
                course=course
            ).exclude(pk=self.instance.pk).values_list(
                "order", flat=True
            )

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
# SUPPORT TICKET ADMIN (CUSTOM)
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
