"""MinIO / S3 object storage wrapper (boto3).

Single bucket holds document bytes. Keys:
  nodes/{node_id}/current
  nodes/{node_id}/versions/{version_id}

Lazily initialized; the boto3 client does not connect until a call is made.
"""
from functools import lru_cache

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import get_settings

settings = get_settings()


class Storage:
    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.minio_endpoint,
            aws_access_key_id=settings.minio_root_user,
            aws_secret_access_key=settings.minio_root_password,
            region_name="us-east-1",
            config=Config(signature_version="s3v4"),
        )
        self.bucket = settings.minio_bucket

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self.bucket)

    def put_bytes(self, key: str, data: bytes, content_type: str | None = None) -> None:
        extra = {"ContentType": content_type} if content_type else {}
        self._client.put_object(Bucket=self.bucket, Key=key, Body=data, **extra)

    def get_bytes(self, key: str) -> bytes:
        resp = self._client.get_object(Bucket=self.bucket, Key=key)
        return resp["Body"].read()

    def copy(self, src_key: str, dst_key: str) -> None:
        self._client.copy_object(
            Bucket=self.bucket,
            CopySource={"Bucket": self.bucket, "Key": src_key},
            Key=dst_key,
        )

    def delete_objects(self, keys: list[str]) -> None:
        if not keys:
            return
        self._client.delete_objects(
            Bucket=self.bucket,
            Delete={"Objects": [{"Key": k} for k in keys], "Quiet": True},
        )


@lru_cache
def get_storage() -> Storage:
    return Storage()
