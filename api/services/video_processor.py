import os
import shutil
import subprocess
import tempfile
from django.conf import settings
from django.core.files.storage import default_storage
from api.models import Video
from api.r2 import upload_hls_folder_to_r2


def process_video_to_hls(video_id):
    video = Video.objects.get(id=video_id)
    local_input_path = None
    hls_dir = None

    try:
        # copy uploaded file
        with default_storage.open(video.source_video.name, "rb") as src:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                for chunk in src.chunks():
                    tmp.write(chunk)
                local_input_path = tmp.name

        lesson_id = f"lesson_{video.id}"
        hls_dir = os.path.join(settings.MEDIA_ROOT, "tmp_hls", lesson_id)
        os.makedirs(hls_dir, exist_ok=True)

        playlist_path = os.path.join(hls_dir, "playlist.m3u8")

        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", local_input_path,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-hls_time", "4",
                "-hls_list_size", "0",
                "-hls_flags", "independent_segments",
                "-hls_segment_filename", f"{hls_dir}/segment_%03d.ts",
                playlist_path,
            ],
            check=True,
        )

        r2_folder = f"videos/course-{video.course.id}/{lesson_id}"
        playlist_url = upload_hls_folder_to_r2(hls_dir, r2_folder)

        return playlist_url   # ✅ IMPORTANT

    finally:
        if local_input_path and os.path.exists(local_input_path):
            os.remove(local_input_path)
        if hls_dir and os.path.exists(hls_dir):
            shutil.rmtree(hls_dir, ignore_errors=True)
