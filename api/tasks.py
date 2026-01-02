from celery import shared_task
from api.models import Video
from api.services.video_processor import process_video_to_hls

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=10, retry_kwargs={"max_retries": 3})
def process_video_task(self, video_id):
    video = Video.objects.get(id=video_id)
    video.status = "processing"
    video.save(update_fields=["status"])

    try:
        playlist_url = process_video_to_hls(video_id)
        video.video_url = playlist_url
        video.status = "ready"
        video.source_video = None
        video.save(update_fields=["video_url", "status", "source_video"])
    except Exception:
        video.status = "failed"
        video.save(update_fields=["status"])
        raise
