from asyncio import gather
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from miniopy_async.api import Minio
from sqlalchemy import and_, case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from db.minio import get_minio_client
from db.session import get_db
from models import Like, RiskFactor
from models.risk_factor import PublicationStatus
from schemas import CreateRiskFactorSchema
from utils.name_gen import generate_file_name


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


@risk_factor_router.delete("/factors/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_risk_factor(
    session: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[int, Depends(get_user_id)],
    factor_id: Annotated[int, Query()],
):
    stmt = "UPDATE risk_faАctors SET publication_status = :new_status WHERE id = :id AND creator_id = :creator_id"

    await session.execute(text(stmt), {"new_status": PublicationStatus.DELETED.value, "id": factor_id, "creator_id": user_id})
    await session.commit()


@risk_factor_router.get("/factors/{factor_id}")
async def get_risk_factor_info(
    factor_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
    next_video: Annotated[bool, Query(alias="next")] = False,
):

    if next_video:
        stmt = (
            select(RiskFactor, func.count(Like.id))
            .outerjoin_from(RiskFactor, Like, RiskFactor.id == Like.risk_factor_id)
            .where(RiskFactor.publication_status == PublicationStatus.PUBLISHED)
            .group_by(RiskFactor.id)
            .order_by(case((RiskFactor.id > factor_id, 0), else_=1), RiskFactor.id.asc())
            .limit(1)
        )
    else:
        stmt = (
            select(RiskFactor, func.count(Like.id))
            .outerjoin_from(RiskFactor, Like, RiskFactor.id == Like.risk_factor_id)
            .where(and_(RiskFactor.publication_status == PublicationStatus.PUBLISHED, RiskFactor.id == factor_id))
            .group_by(RiskFactor.id)
        )

    res = await session.execute(stmt)
    res = res.one_or_none()
    if res is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="не удалось найти фактор риска")

    risk_factor, likes = res
    return {"risk_factor": risk_factor, "likes": likes}


@risk_factor_router.get("factors/reels")
async def get_feed(session: Annotated[AsyncSession, Depends(get_db)]):
    stmt = (
        select(RiskFactor, func.count(Like.id))
        .outerjoin_from(RiskFactor, Like, RiskFactor.id == Like.risk_factor_id)
        .where(RiskFactor.publication_status == PublicationStatus.PUBLISHED)
        .group_by(RiskFactor.id)
        .limit(1)
    )
    res = await session.execute(stmt)

    res = res.one_or_none()
    if res is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="не удалось найти фактор риска")

    risk_factor, likes = res
    return {"risk_factor": risk_factor, "likes": likes}


@risk_factor_router.get("factors/draft")
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


@risk_factor_router.post("factors/draft", status_code=status.HTTP_201_CREATED)
async def create_draft_factor(
    session: Annotated[AsyncSession, Depends(get_db)],
    minio_client: Annotated[Minio, Depends(get_minio_client)],
    user_id: Annotated[int, Depends(get_user_id)],
    risk_factor: CreateRiskFactorSchema,
    image: UploadFile,
    video: UploadFile,
):
    if not image.content_type or not image.filename or not image.content_type.startswith("/image"):
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="файл image не является изображением")

    if not video.content_type or not video.filename or not video.content_type.startswith("/video"):
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="файл vide не является видео")

    image_name, video_name = generate_file_name(Path(image.filename).suffix), generate_file_name(Path(video.filename).suffix)
    image_content, video_content = await gather(*[image.read(), video.read()])
    await gather(
        *[
            minio_client.append_object(BUCKET_NAME, object_name=image_name, data=BytesIO(image_content), length=len(image_content)),
            minio_client.append_object(BUCKET_NAME, object_name=video_name, data=BytesIO(video_content), length=len(video_content)),
        ]
    )

    stmt = (
        select(RiskFactor).where(and_(RiskFactor.creator_id == user_id, RiskFactor.publication_status == PublicationStatus.DRAFT)).limit(1)
    )

    res = await session.execute(stmt)
    factor = res.scalar_one_or_none()
    if factor:
        factor.name = risk_factor.name
        factor.description = risk_factor.description
        factor.weight = risk_factor.weight
        factor.prevalence = risk_factor.prevalence
        factor.category = risk_factor.category
        factor.creator_id = user_id
        factor.image_url = image_name
        factor.video_url = video_name
    else:
        factor = RiskFactor(
            name=risk_factor.name,
            description=risk_factor.description,
            weight=risk_factor.weight,
            prevalence=risk_factor.prevalence,
            category=risk_factor.category,
            creator_id=user_id,
            image_url=image_name,
            video_url=video_name,
        )
        session.add(factor)

    await session.commit()
    return factor


@risk_factor_router.put("factors/draft", status_code=status.HTTP_200_OK)
async def publish_factor(
    session: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[int, Depends(get_user_id)],
):
    stmt = select(RiskFactor).where(
        and_(
            RiskFactor.publication_status == PublicationStatus.DRAFT,
            RiskFactor.creator_id == user_id,
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


@risk_factor_router.post("factors/like", status_code=status.HTTP_204_NO_CONTENT)
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
