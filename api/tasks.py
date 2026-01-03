from celery import shared_task
from api.models import Video
from api.services.video_processor import process_video_to_hls

@shared_task(bind=True, autoretry_for=(), retry_kwargs={"max_retries": 0})
def process_video_task(self, video_id):
    from api.services.video_processor import process_video_to_hls
    video = Video.objects.get(id=video_id)

    try:
        video.stage = "converting"
        video.progress = 0
        video.save(update_fields=["stage", "progress"])

        playlist_url = process_video_to_hls(video)

        video.status = "ready"     # 🔥 MISSING LINE
        video.stage = "ready"
        video.progress = 100
        video.video_url = playlist_url
        video.source_video = None
        video.save(update_fields=[
            "status", "stage", "progress", "video_url", "source_video"
        ])


    except Exception as e:
        video.status = "failed"
        video.stage = "failed"
        video.log = (video.log or "") + f"\nERROR: {str(e)}"
        video.save(update_fields=["status", "stage", "log"])
        raise

