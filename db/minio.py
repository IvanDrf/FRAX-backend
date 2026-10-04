from miniopy_async.api import Minio

from core.config import settings

minio_client = Minio(
    endpoint=settings.MINIO_URL,
    access_key=settings.MINIO_USER,
    secret_key=settings.MINIO_PASSWORD,
)


async def get_minio_client() -> Minio:
    return minio_client
