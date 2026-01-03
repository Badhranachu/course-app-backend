import os
import shutil
import subprocess
import tempfile
import logging
from django.conf import settings
from api.models import Video
from api.r2 import download_from_r2, upload_hls_folder_to_r2

logger = logging.getLogger(__name__)


def process_video_to_hls(video: Video) -> str:
    """
    FULL PIPELINE:
    1. Download raw video from R2
    2. Convert to HLS with FFmpeg (real progress)
    3. Upload HLS back to R2
    """

    # -----------------------------
    # INITIAL STATE
    # -----------------------------
    video.stage = "downloading"
    video.progress = 0
    video.save(update_fields=["stage", "progress"])

    local_input = None
    hls_dir = None

    try:
        # -----------------------------
        # 1️⃣ DOWNLOAD FROM R2
        # -----------------------------
        logger.info(f"Downloading video {video.id} from R2")

        local_input = download_from_r2(video.source_video.name)

        logger.info(f"Downloaded to local file: {local_input}")

        # -----------------------------
        # PREPARE HLS FOLDER
        # -----------------------------
        lesson_id = f"lesson_{video.id}"
        hls_dir = os.path.join(settings.MEDIA_ROOT, "tmp_hls", lesson_id)
        os.makedirs(hls_dir, exist_ok=True)

        playlist_path = os.path.join(hls_dir, "playlist.m3u8")

        # -----------------------------
        # 2️⃣ FFmpeg CONVERSION (REAL PROGRESS)
        # -----------------------------
        video.stage = "converting"
        video.progress = 0
        video.save(update_fields=["stage", "progress"])

        logger.info("Starting FFmpeg conversion")

        cmd = [
            "/usr/bin/ffmpeg", "-y",
            "-i", local_input,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-c:a", "aac",
            "-hls_time", "4",
            "-hls_list_size", "0",
            "-hls_flags", "independent_segments",
            "-hls_segment_filename",
            os.path.join(hls_dir, "segment_%03d.ts"),
            playlist_path,
            "-progress", "pipe:1",
            "-nostats",
        ]



        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        for line in process.stdout:
            if line.startswith("out_time_ms"):
                try:
                    ms = int(line.strip().split("=")[1])
                    percent = min(99, ms // 100000)
                    video.progress = percent
                    video.save(update_fields=["progress"])
                except Exception:
                    pass

        process.wait()

        if process.returncode != 0:
            raise RuntimeError("FFmpeg conversion failed")

        logger.info("FFmpeg conversion finished")

        # -----------------------------
        # 3️⃣ UPLOAD HLS TO R2
        # -----------------------------
        video.stage = "uploading_hls"
        video.progress = 0
        video.save(update_fields=["stage", "progress"])

        playlist_url = upload_hls_folder_to_r2(
            hls_dir,
            f"videos/course-{video.course.id}/{lesson_id}",
            video=video,  # 👈 allow progress updates inside uploader
        )

        logger.info(f"HLS uploaded successfully: {playlist_url}")

        return playlist_url

    except Exception as e:
        logger.exception("Video processing failed")
        raise e

    finally:
        # -----------------------------
        # CLEANUP (SAFE)
        # -----------------------------
        if local_input and os.path.exists(local_input):
            os.remove(local_input)

        if hls_dir and os.path.exists(hls_dir):
            shutil.rmtree(hls_dir, ignore_errors=True)
