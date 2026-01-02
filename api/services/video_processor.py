import os
import shutil
import subprocess
from django.conf import settings
from api.models import Video
from api.r2 import download_from_r2
from api.r2 import upload_hls_folder_to_r2


def process_video_to_hls(video_id: int) -> str:
    video = Video.objects.get(id=video_id)

    # 1️⃣ Download from R2 → local
    local_input = download_from_r2(video.source_video.name)

    lesson_id = f"lesson_{video.id}"
    hls_dir = os.path.join(settings.MEDIA_ROOT, "tmp_hls", lesson_id)
    os.makedirs(hls_dir, exist_ok=True)

    playlist_path = os.path.join(hls_dir, "playlist.m3u8")

    try:
        # 2️⃣ Convert to HLS
        subprocess.run(
            [
                "/usr/bin/ffmpeg", "-y",
                "-i", local_input,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "23",
                "-c:a", "aac",
                "-hls_time", "4",
                "-hls_list_size", "0",
                "-hls_flags", "independent_segments",
                "-hls_segment_filename", f"{hls_dir}/segment_%03d.ts",
                playlist_path,
            ],
            check=True,
        )

        # 3️⃣ Upload HLS back to R2
        return upload_hls_folder_to_r2(
            hls_dir,
            f"videos/course-{video.course.id}/{lesson_id}"
        )

    finally:
        if os.path.exists(local_input):
            os.remove(local_input)

        shutil.rmtree(hls_dir, ignore_errors=True)
