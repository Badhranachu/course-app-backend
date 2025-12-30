

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


def upload_video_to_r2(file, folder):
    # 🔹 Read directly from .env
    R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
    R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
    R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
    R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
    R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL")

    R2_ENDPOINT_URL = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

    # 🔒 Safety check
    if not all([
        R2_ACCESS_KEY_ID,
        R2_SECRET_ACCESS_KEY,
        R2_BUCKET_NAME,
        R2_ACCOUNT_ID,
        R2_PUBLIC_URL,
    ]):
        raise ValueError("Missing Cloudflare R2 environment variables")

    s3 = boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )

    # File name
    ext = file.name.rsplit(".", 1)[-1].lower()
    key = f"{folder}/{uuid.uuid4()}.{ext}"

    # IMPORTANT for admin uploads
    file.seek(0)

    s3.upload_fileobj(
        file,
        R2_BUCKET_NAME,
        key,
        ExtraArgs={
            "ContentType": "video/mp4"
        }

    )

    return f"{R2_PUBLIC_URL}/{key}"
