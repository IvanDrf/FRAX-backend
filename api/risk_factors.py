from asyncio import gather
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path as Pathlib
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, HTTPException, Path, Query, UploadFile, status
from miniopy_async.api import Minio
from miniopy_async.error import MinioException
from sqlalchemy import and_, case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.minio import get_minio_client
from db.session import get_db
from models import Like, RiskFactor
from models.risk_factor import FactorCategory, PublicationStatus


def get_user_id() -> int:
    return 1


risk_factor_router = APIRouter(prefix="/api", tags=["frax"])


@risk_factor_router.get("/factors")
async def get_risk_factors(
    session: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[int, Depends(get_user_id)],
    risk_factor_weight: float | None = None,
):
    stmt = (
        select(RiskFactor, func.count(Like.id))
        .outerjoin_from(RiskFactor, Like, RiskFactor.id == Like.risk_factor_id)
        .where(RiskFactor.publication_status == PublicationStatus.PUBLISHED)
    )

    if risk_factor_weight is not None:
        stmt = stmt.where(RiskFactor.weight > risk_factor_weight)

    stmt = stmt.group_by(RiskFactor.id)

    res = await session.execute(stmt)
    result: list[dict[str, Any]] = []

    for row in res:
        result.append({"risk_factor": row[0], "likes": row[1], "is_creator": row[0].creator_id == user_id})

    return result


@risk_factor_router.delete("/factors/{risk_factor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_risk_factor(
    session: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[int, Depends(get_user_id)],
    risk_factor_id: Annotated[int, Path()],
):
    stmt = "UPDATE risk_factors SET publication_status = :new_status WHERE id = :id AND creator_id = :creator_id"

    await session.execute(text(stmt), {"new_status": PublicationStatus.DELETED.value, "id": risk_factor_id, "creator_id": user_id})
    await session.commit()


@risk_factor_router.get("/factors/reels")
async def get_risk_factor_info(
    session: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[int, Depends(get_user_id)],
    risk_factor_id: int | None = None,
    next_video: Annotated[bool, Query(alias="next")] = False,
):
    user_liked = func.bool_or(case((Like.user_id == user_id, True), else_=False))

    if next_video and risk_factor_id is not None:
        stmt = (
            select(RiskFactor, func.count(Like.id), user_liked)
            .outerjoin_from(RiskFactor, Like, RiskFactor.id == Like.risk_factor_id)
            .where(RiskFactor.publication_status == PublicationStatus.PUBLISHED)
            .group_by(RiskFactor.id)
            .order_by(case((RiskFactor.id > risk_factor_id, 0), else_=1), RiskFactor.id.asc())
            .limit(1)
        )
    else:
        stmt = (
            select(RiskFactor, func.count(Like.id), user_liked)
            .outerjoin_from(RiskFactor, Like, RiskFactor.id == Like.risk_factor_id)
            .where(RiskFactor.publication_status == PublicationStatus.PUBLISHED)
            .group_by(RiskFactor.id)
            .limit(1)
        )

    res = await session.execute(stmt)
    res = res.one_or_none()
    if res is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="не удалось найти фактор риска")

    risk_factor, likes, is_liked = res
    return {"risk_factor": risk_factor, "likes": likes, "is_liked": is_liked}


@risk_factor_router.get("/factors/draft")
async def get_draft_factor(session: Annotated[AsyncSession, Depends(get_db)], user_id: Annotated[int, Depends(get_user_id)]):
    stmt = (
        select(RiskFactor).where(and_(RiskFactor.creator_id == user_id, RiskFactor.publication_status == PublicationStatus.DRAFT)).limit(1)
    )

    res = await session.execute(stmt)
    risk_factor = res.scalar_one_or_none()
    if risk_factor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="не удалось найти черновик")

    return {"risk_factor": risk_factor}


BUCKET_NAME = "frax-bucket"


@risk_factor_router.post("/factors/draft", status_code=status.HTTP_201_CREATED)
async def create_draft_factor(
    session: Annotated[AsyncSession, Depends(get_db)],
    minio_client: Annotated[Minio, Depends(get_minio_client)],
    user_id: Annotated[int, Depends(get_user_id)],
    name: Annotated[str, Form()],
    description: Annotated[str, Form()],
    weight: Annotated[int, Form(ge=0, le=2)],
    prevalence: Annotated[int | None, Form(ge=0, le=100)],
    category: Annotated[FactorCategory, Form()],
    image: UploadFile,
    video: UploadFile,
):
    if not image.content_type or not image.filename or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="файл image не является изображением")

    if not video.content_type or not video.filename or not video.content_type.startswith("video/"):
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="файл vide не является видео")

    stmt = (
        select(RiskFactor).where(and_(RiskFactor.creator_id == user_id, RiskFactor.publication_status == PublicationStatus.DRAFT)).limit(1)
    )

    res = await session.execute(stmt)
    factor = res.scalar_one_or_none()
    if factor is None:
        factor = RiskFactor()

    factor.name = name
    factor.description = description
    factor.weight = weight
    factor.prevalence = prevalence
    factor.category = category
    factor.creator_id = user_id
    factor.image_url = ""
    factor.video_url = ""
    session.add(factor)
    await session.flush()

    image_name, video_name = (
        generate_filename(factor.id, Pathlib(image.filename).suffix),
        generate_filename(factor.id, Pathlib(video.filename).suffix),
    )
    factor.image_url = generate_file_url(image_name)
    factor.video_url = generate_file_url(video_name)

    try:
        image_content, video_content = await gather(*[image.read(), video.read()])
        await gather(
            *[
                minio_client.put_object(BUCKET_NAME, object_name=image_name, data=BytesIO(image_content), length=len(image_content)),
                minio_client.put_object(BUCKET_NAME, object_name=video_name, data=BytesIO(video_content), length=len(video_content)),
            ]
        )

    except MinioException:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="не удалось сохранить файлы")

    await session.commit()
    return factor


@risk_factor_router.put("/factors/draft/{factor_id}", status_code=status.HTTP_200_OK)
async def publish_factor(
    session: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[int, Depends(get_user_id)],
    factor_id: Annotated[int, Path()],
):
    stmt = select(RiskFactor).where(
        and_(
            RiskFactor.publication_status == PublicationStatus.DRAFT,
            RiskFactor.creator_id == user_id,
            RiskFactor.id == factor_id,
        )
    )
    res = await session.execute(stmt)
    risk_factor = res.scalar_one_or_none()

    if risk_factor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="не удалось найти черновик")

    risk_factor.publication_status = PublicationStatus.PUBLISHED
    risk_factor.formated_at = datetime.now(timezone(offset=timedelta(hours=3)))

    await session.commit()
    return risk_factor


@risk_factor_router.post("/factors/like", status_code=status.HTTP_204_NO_CONTENT)
async def add_like(
    risk_factor_id: int,
    add_like: bool,
    session: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[int, Depends(get_user_id)],
):
    stmt = select(Like).where(and_(Like.user_id == user_id, Like.risk_factor_id == risk_factor_id))
    res = await session.execute(stmt)
    like = res.scalar_one_or_none()

    if like is None and not add_like:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="нельзя отменить лайк, который еще не ставили")

    if like is not None and add_like:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="нельзя дважды ставить лайк")

    if add_like:
        session.add(Like(user_id=user_id, risk_factor_id=risk_factor_id))
    else:
        await session.delete(like)

    await session.commit()


def generate_filename(id: int, ext: str) -> str:
    ext = ext if ext.startswith(".") else "." + ext
    return f"{id}{ext}"


def generate_file_url(name: str) -> str:
    return f"http://{settings.MINIO_HOST}:{settings.MINIO_PORT}/{BUCKET_NAME}/{name}"
