

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
