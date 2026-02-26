from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0062_seoprofile"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductEnquiry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enquiry_type", models.CharField(choices=[("product", "Product"), ("section", "Section")], max_length=20)),
                ("section_key", models.CharField(blank=True, max_length=50)),
                ("section_title", models.CharField(blank=True, max_length=200)),
                ("product_id", models.CharField(blank=True, max_length=120)),
                ("product_name", models.CharField(blank=True, max_length=200)),
                ("selected_items", models.JSONField(blank=True, default=list)),
                ("full_name", models.CharField(max_length=150)),
                ("phone", models.CharField(max_length=20)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("custom_message", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("contacted", "Contacted")], default="pending", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
