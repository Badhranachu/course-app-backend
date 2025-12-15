from django.db.models.signals import post_save
from django.dispatch import receiver
from api.models import CustomUser,AdminProfile,StudentProfile

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.role == "admin":
        AdminProfile.objects.create(
            user=instance,
            full_name=instance.email.split("@")[0]
        )

    elif instance.role == "student":
        StudentProfile.objects.create(
            user=instance,
            full_name=instance.email.split("@")[0]
        )
