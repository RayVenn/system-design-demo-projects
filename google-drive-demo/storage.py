import boto3
from botocore.exceptions import ClientError

from config import settings


def _s3_client():
    kwargs = {
        "region_name": settings.aws_region,
    }
    if settings.aws_access_key_id:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    return boto3.client("s3", **kwargs)


def ensure_bucket_exists() -> None:
    s3 = _s3_client()
    try:
        s3.head_bucket(Bucket=settings.s3_bucket)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("404", "NoSuchBucket"):
            if settings.aws_region == "us-east-1":
                s3.create_bucket(Bucket=settings.s3_bucket)
            else:
                s3.create_bucket(
                    Bucket=settings.s3_bucket,
                    CreateBucketConfiguration={"LocationConstraint": settings.aws_region},
                )
        else:
            raise


def generate_presigned_upload_url(s3_key: str) -> str:
    s3 = _s3_client()
    return s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.s3_bucket, "Key": s3_key},
        ExpiresIn=settings.presigned_url_expiry_seconds,
    )


def generate_presigned_download_url(s3_key: str) -> str:
    s3 = _s3_client()
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": s3_key},
        ExpiresIn=settings.presigned_url_expiry_seconds,
    )


def delete_object(s3_key: str) -> None:
    s3 = _s3_client()
    s3.delete_object(Bucket=settings.s3_bucket, Key=s3_key)
