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


    

import threading
from django.db.models.signals import post_save
from django.dispatch import receiver
from api.models import Video
from api.services.video_processor import process_video_to_hls

@receiver(post_save, sender=Video)
def auto_process_video(sender, instance, created, **kwargs):
    if created and instance.source_video:
        threading.Thread(
            target=process_video_to_hls,
            args=(instance,),
            daemon=True
        ).start()

