from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0063_productenquiry"),
    ]

    operations = [
        migrations.CreateModel(
            name="SEOChangeBackup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "entity_type",
                    models.CharField(
                        choices=[("page", "Page"), ("course", "Course"), ("job", "Job")],
                        max_length=20,
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        choices=[("create", "Create"), ("update", "Update"), ("delete", "Delete")],
                        max_length=20,
                    ),
                ),
                ("entity_id", models.CharField(blank=True, max_length=50)),
                ("object_id", models.IntegerField(blank=True, null=True)),
                ("object_label", models.CharField(blank=True, max_length=255)),
                ("changed_fields", models.JSONField(blank=True, default=list)),
                ("before_data", models.JSONField(blank=True, default=dict)),
                ("after_data", models.JSONField(blank=True, default=dict)),
                ("changed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "changed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="seo_change_backups",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-changed_at"],
            },
        ),
    ]
