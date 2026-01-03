

import boto3
from django.conf import settings

def upload_pdf_to_r2(file_bytes, object_key):
    s3 = boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,  # ✅ USE THIS
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )

    s3.put_object(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        Key=object_key,
        Body=file_bytes,
        ContentType="application/pdf",
    )

    return f"{settings.R2_PUBLIC_URL}/{object_key}"



import os
import uuid
import boto3


import os
import boto3
import mimetypes
import logging

logger = logging.getLogger(__name__)


def upload_folder_recursive_to_r2(local_folder, r2_prefix):
    logger.info("☁️ Initializing Cloudflare R2 client")

    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
    )

    bucket = os.getenv("R2_BUCKET_NAME")

    for root, _, files in os.walk(local_folder):
        for file in files:
            local_path = os.path.join(root, file)
            rel_path = os.path.relpath(local_path, local_folder)
            r2_key = f"{r2_prefix}/{rel_path}".replace("\\", "/")

            logger.info(f"⬆️ Uploading: {r2_key}")

            extra = {}
            if file.endswith(".m3u8"):
                extra["ContentType"] = "application/vnd.apple.mpegurl"
            elif file.endswith(".ts"):
                extra["ContentType"] = "video/mp2t"

            s3.upload_file(
                local_path,
                bucket,
                r2_key,
                ExtraArgs=extra
            )

    logger.info("☁️ All files uploaded to R2")





import tempfile
import os
from django.core.files.storage import default_storage


def download_from_r2(r2_key: str) -> str:
    """
    Downloads a file from Cloudflare R2 to a local temp file
    and returns the local file path.

    :param r2_key: Path/key of the file in R2 (e.g. uploads/video.mp4)
    :return: local file path
    """

    if not default_storage.exists(r2_key):
        raise FileNotFoundError(f"R2 object not found: {r2_key}")

    suffix = os.path.splitext(r2_key)[1] or ".mp4"

    with default_storage.open(r2_key, "rb") as remote_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            for chunk in remote_file:
                tmp.write(chunk)
            return tmp.name
