from __future__ import annotations

import logging
import os
from typing import Any, Sequence

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from core.application.interfaces.services import StorageBackend

logger = logging.getLogger(__name__)


class S3Storage(StorageBackend):
    """AWS S3 / MinIO implementation of StorageBackend ABC.

    Configuration via environment variables:
        AWS_ACCESS_KEY_ID     - AWS access key (or MinIO equivalent)
        AWS_SECRET_ACCESS_KEY - AWS secret key (or MinIO equivalent)
        AWS_DEFAULT_REGION    - AWS region (default: us-east-1)
        S3_BUCKET             - Target bucket name
        S3_ENDPOINT_URL       - Custom endpoint for MinIO / LocalStack
    """

    def __init__(
        self,
        bucket: str | None = None,
        endpoint_url: str | None = None,
    ) -> None:
        self._bucket = bucket or os.getenv("S3_BUCKET", "ai-archive-storage")
        self._endpoint_url = endpoint_url or os.getenv("S3_ENDPOINT_URL")

        self._client = boto3.client(
            "s3",
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
            endpoint_url=self._endpoint_url,
        )
        logger.info(
            "S3Storage initialized (bucket=%s, endpoint=%s)",
            self._bucket,
            self._endpoint_url or "default",
        )

    def _handle_client_error(self, exc: ClientError, path: str, operation: str) -> None:
        code = exc.response.get("Error", {}).get("Code", "")
        if code == "NoSuchKey" or code == "404":
            raise FileNotFoundError(f"File not found in S3: {path}") from exc
        logger.error("S3 %s failed for %s: %s", operation, path, exc)
        raise

    async def save(
        self,
        content: bytes,
        path: str,
        *,
        content_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        try:
            extra: dict[str, Any] = {}
            if content_type:
                extra["ContentType"] = content_type
            if metadata:
                extra["Metadata"] = {k: str(v) for k, v in metadata.items()}

            self._client.put_object(
                Bucket=self._bucket,
                Key=path,
                Body=content,
                **extra,
            )
            logger.debug("Uploaded %d bytes to s3://%s/%s", len(content), self._bucket, path)
            return path
        except ClientError as exc:
            self._handle_client_error(exc, path, "put_object")

    async def retrieve(self, path: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=path)
            data = response["Body"].read()
            logger.debug("Downloaded %d bytes from s3://%s/%s", len(data), self._bucket, path)
            return data
        except ClientError as exc:
            self._handle_client_error(exc, path, "get_object")
            return b""  # unreachable, keeps type checker happy

    async def delete(self, path: str) -> bool:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=path)
            logger.debug("Deleted s3://%s/%s", self._bucket, path)
            return True
        except ClientError as exc:
            self._handle_client_error(exc, path, "delete_object")
            return False  # unreachable

    async def list(
        self,
        prefix: str = "",
        *,
        limit: int = 1000,
    ) -> Sequence[str]:
        try:
            paginator = self._client.get_paginator("list_objects_v2")
            results: list[str] = []
            for page in paginator.paginate(
                Bucket=self._bucket,
                Prefix=prefix,
                PaginationConfig={"MaxItems": limit},
            ):
                for obj in page.get("Contents", []):
                    results.append(obj["Key"])
                    if len(results) >= limit:
                        break
                if len(results) >= limit:
                    break
            return results
        except ClientError as exc:
            logger.error("S3 list failed for prefix '%s': %s", prefix, exc)
            return []

    async def get_url(self, path: str, *, expires_in: int = 3600) -> str:
        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": path},
                ExpiresIn=expires_in,
            )
            return url
        except (ClientError, NoCredentialsError) as exc:
            logger.error("Failed to generate pre-signed URL for %s: %s", path, exc)
            raise FileNotFoundError(f"File not found in S3: {path}") from exc

    async def exists(self, path: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=path)
            return True
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code == "404" or code == "NoSuchKey":
                return False
            raise
