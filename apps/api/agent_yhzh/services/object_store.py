import asyncio
from pathlib import Path

from agent_yhzh.config import settings


def _safe_local_path(object_key: str) -> Path:
    root = settings.object_store_directory.resolve()
    target = (root / object_key).resolve()
    if root not in target.parents:
        raise ValueError("invalid_object_key")
    return target


async def put_object(object_key: str, data: bytes, mime_type: str) -> None:
    if settings.object_store_backend == "s3":
        import boto3

        def upload() -> None:
            client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                region_name=settings.s3_region,
            )
            try:
                client.head_bucket(Bucket=settings.s3_bucket)
            except Exception:
                client.create_bucket(Bucket=settings.s3_bucket)
            client.put_object(
                Bucket=settings.s3_bucket,
                Key=object_key,
                Body=data,
                ContentType=mime_type,
            )

        await asyncio.to_thread(upload)
        return

    path = _safe_local_path(object_key)

    def write() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    await asyncio.to_thread(write)


async def get_object(object_key: str) -> bytes:
    if settings.object_store_backend == "s3":
        import boto3

        def download() -> bytes:
            client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                region_name=settings.s3_region,
            )
            return client.get_object(Bucket=settings.s3_bucket, Key=object_key)[
                "Body"
            ].read()

        return await asyncio.to_thread(download)
    return await asyncio.to_thread(_safe_local_path(object_key).read_bytes)
