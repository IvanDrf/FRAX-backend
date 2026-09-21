from datetime import datetime, timedelta, timezone
from typing import Annotated, Final

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models import Like, RiskFactor
from models.risk_factor import FactorCategory, PublicationStatus

TEMPLATES_PATH: Final[str] = "./templates"
DEFAULT_IMAGE: Final[str] = "default.png"
DEFAULT_VIDEO: Final[str] = "default.mp4"

risk_factor_router = APIRouter(tags=["frax"])
templates = Jinja2Templates(TEMPLATES_PATH)


@risk_factor_router.get("/")
async def get_risk_factors(request: Request, session: Annotated[AsyncSession, Depends(get_db)], risk_factor_weight: float | None = None):
    stmt = (
        select(RiskFactor, func.count(Like.id))
        .outerjoin_from(RiskFactor, Like, RiskFactor.id == Like.risk_factor_id)
        .where(RiskFactor.publication_status == PublicationStatus.PUBLISHED)
    )

    if risk_factor_weight is not None:
        stmt = stmt.where(RiskFactor.weight > risk_factor_weight)

    stmt = stmt.group_by(RiskFactor.id)

    res = await session.execute(stmt)
    risk_factors = []
    likes = []

    for row in res:
        risk_factors.append(row[0])
        likes.append(row[1])

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"risk_factors": risk_factors, "risk_factor_weight": risk_factor_weight, "likes_count": likes},
    )


@risk_factor_router.post("/factor/delete")
async def delete_risk_factor(session: Annotated[AsyncSession, Depends(get_db)], factor_id: Annotated[int, Form()]):
    stmt = "UPDATE risk_factors SET publication_status = :new_status WHERE id = :id"

    await session.execute(text(stmt), {"new_status": PublicationStatus.DELETED.value, "id": factor_id})
    await session.commit()

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@risk_factor_router.get("/factor/{factor_id}")
async def get_risk_factor_info(
    request: Request,
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

    factor, likes = res

    return templates.TemplateResponse(
        request=request,
        name="reels.html",
        context={"factor": factor, "likes_count": likes},
    )


@risk_factor_router.get("/reels")
async def get_feed(request: Request, session: Annotated[AsyncSession, Depends(get_db)]):
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

    factor, likes = res
    return templates.TemplateResponse(request=request, name="reels.html", context={"factor": factor, "likes_count": likes})


@risk_factor_router.get("/add")
async def get_draft_factor(request: Request, session: Annotated[AsyncSession, Depends(get_db)], user_id: int = 1):
    stmt = (
        select(RiskFactor).where(and_(RiskFactor.creator_id == user_id, RiskFactor.publication_status == PublicationStatus.DRAFT)).limit(1)
    )

    res = await session.execute(stmt)
    factor = res.scalar_one_or_none()

    return templates.TemplateResponse(request=request, name="addition.html", context={"factor": factor})


@risk_factor_router.post("/add")
async def create_draft_factor(
    session: Annotated[AsyncSession, Depends(get_db)],
    name: Annotated[str, Form()],
    user_id: int = 1,
    image_url: Annotated[str | None, Form()] = None,
    video_url: Annotated[str | None, Form()] = None,
):
    stmt = (
        select(RiskFactor).where(and_(RiskFactor.creator_id == user_id, RiskFactor.publication_status == PublicationStatus.DRAFT)).limit(1)
    )

    res = await session.execute(stmt)
    factor = res.scalar_one_or_none()
    if factor:
        factor.name = name
        factor.image_url = image_url
        factor.video_url = video_url
        factor.creator_id = user_id
    else:
        factor = RiskFactor(name=name, image_url=image_url, video_url=video_url, creator_id=user_id)
        session.add(factor)

    await session.commit()

    return RedirectResponse("/add", status_code=status.HTTP_303_SEE_OTHER)


@risk_factor_router.post("/add/publish")
async def publish_factor(
    session: Annotated[AsyncSession, Depends(get_db)],
    name: Annotated[str, Form()],
    description: Annotated[str, Form()],
    weight: Annotated[float, Form()],
    prevalence: Annotated[int, Form()],
    category: Annotated[str, Form()],
    image_url: Annotated[str | None, Form()] = None,
    video_url: Annotated[str | None, Form()] = None,
    user_id: int = 1,
):
    stmt = select(RiskFactor).where(
        and_(
            RiskFactor.publication_status == PublicationStatus.DRAFT,
            RiskFactor.creator_id == user_id,
        )
    )
    res = await session.execute(stmt)
    factor = res.scalar_one_or_none()

    if factor is None:
        raise HTTPException(status_code=404, detail="Черновик не найден")

    factor.name = name
    factor.description = description
    factor.weight = weight
    factor.prevalence = prevalence
    factor.category = FactorCategory(category)
    factor.image_url = image_url
    factor.video_url = video_url
    factor.publication_status = PublicationStatus.PUBLISHED
    factor.formated_at = datetime.now(timezone(timedelta(hours=3)))

    await session.commit()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
