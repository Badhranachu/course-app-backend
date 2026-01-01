import os
import uuid
import subprocess
import shutil
from django.conf import settings

import os
import shutil
import subprocess
from django.conf import settings
from api.r2 import upload_hls_folder_to_r2
import os
import shutil
import subprocess
import tempfile

from django.conf import settings
from django.core.files.storage import default_storage

from api.r2 import upload_hls_folder_to_r2


def process_video_to_hls(video):
    """
    Converts uploaded video → HLS → Uploads to R2 → Saves playlist URL
    """

    # 1️⃣ Copy uploaded file to local temp file
    with default_storage.open(video.source_video.name, "rb") as src:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            for chunk in src.chunks():
                tmp.write(chunk)
            local_input_path = tmp.name

    # 2️⃣ Stable lesson folder
    lesson_id = f"lesson_{video.id}"
    hls_dir = os.path.join(settings.MEDIA_ROOT, "tmp_hls", lesson_id)
    os.makedirs(hls_dir, exist_ok=True)

    playlist_path = os.path.join(hls_dir, "playlist.m3u8")

    # 3️⃣ FFmpeg conversion
    cmd = [
        "ffmpeg", "-y",
        "-i", local_input_path,
        "-c:v", "libx264",
        "-profile:v", "main",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-hls_time", "4",
        "-hls_list_size", "0",
        "-hls_flags", "independent_segments",
        "-hls_segment_filename", f"{hls_dir}/segment_%03d.ts",
        playlist_path,
    ]

    subprocess.run(cmd, check=True)

    # 4️⃣ Upload HLS to Cloudflare R2
    r2_folder = f"videos/course-{video.course.id}/{lesson_id}"
    playlist_url = upload_hls_folder_to_r2(hls_dir, r2_folder)

    # 5️⃣ Save URL
    video.video_url = playlist_url

    # 6️⃣ Delete original uploaded file (remote)
    video.source_video.delete(save=False)
    video.source_video = None
    video.save(update_fields=["video_url", "source_video"])

    # 7️⃣ Cleanup local temp files
    os.remove(local_input_path)
    shutil.rmtree(hls_dir, ignore_errors=True)