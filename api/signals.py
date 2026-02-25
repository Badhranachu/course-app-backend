from django.db.models.signals import post_save
from django.dispatch import receiver

from api.models import AdminProfile, CustomUser, SEOProfile, Video


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.role == "admin":
        AdminProfile.objects.get_or_create(
            user=instance,
            defaults={"full_name": instance.email.split("@")[0]},
        )

    elif instance.role == "seo":
        SEOProfile.objects.get_or_create(
            user=instance,
            defaults={"full_name": instance.email.split("@")[0]},
        )


@receiver(post_save, sender=Video)
def auto_process_video(sender, instance, created, **kwargs):
    # Kept safe no-op: this project currently uses manual/other upload pipeline.
    # Avoid runtime crashes from missing fields/services.
    return
