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


def upload_chunk(s3_key: str, data: bytes) -> None:
    s3 = _s3_client()
    s3.put_object(Bucket=settings.s3_bucket, Key=s3_key, Body=data)


def download_chunk(s3_key: str) -> bytes:
    s3 = _s3_client()
    response = s3.get_object(Bucket=settings.s3_bucket, Key=s3_key)
    return response["Body"].read()


def delete_chunks(s3_keys: list[str]) -> None:
    if not s3_keys:
        return
    s3 = _s3_client()
    objects = [{"Key": key} for key in s3_keys]
    s3.delete_objects(Bucket=settings.s3_bucket, Delete={"Objects": objects})
