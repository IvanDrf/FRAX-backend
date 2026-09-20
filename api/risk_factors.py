from typing import Annotated, Final

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.templating import Jinja2Templates

from models.risk_factors import RISK_FACTORS, is_risk_factor_drafted, is_risk_factor_published, is_risk_factor_weight_bigger

TEMPLATES_PATH: Final[str] = "./templates"

risk_factor_router = APIRouter(tags=["frax"])
templates = Jinja2Templates(TEMPLATES_PATH)


@risk_factor_router.get("/")
def get_risk_factors(request: Request, risk_factor_weight: float | None = None):
    if risk_factor_weight is None:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"risk_factors": [risk_factor for risk_factor in RISK_FACTORS if is_risk_factor_published(risk_factor)]},
        )

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "risk_factors": [
                risk_factor
                for risk_factor in RISK_FACTORS
                if is_risk_factor_weight_bigger(risk_factor, risk_factor_weight) and is_risk_factor_published(risk_factor)
            ],
            "risk_factor_weight": risk_factor_weight,
        },
    )


@risk_factor_router.get("/factor/{factor_id}")
def get_risk_factor_info(request: Request, factor_id: int, next_video: Annotated[bool, Query(alias="next")] = False):
    published_factors = [risk_factor for risk_factor in RISK_FACTORS if is_risk_factor_published(risk_factor)]

    if not next_video:
        return templates.TemplateResponse(
            request=request,
            name="reels.html",
            context={"factor": next(factor for factor in published_factors if factor.get("factor_id") == factor_id)},
        )

    for published_factor_id, factor in enumerate(published_factors):
        if factor.get("factor_id") == factor_id:
            return templates.TemplateResponse(
                request=request,
                name="reels.html",
                context={"factor": published_factors[(published_factor_id + 1) % len(published_factors)]},
            )

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="не удалось найти фактор риска")


@risk_factor_router.get("/reels")
def get_feed(request: Request):
    for factor in RISK_FACTORS:
        if is_risk_factor_published(factor):
            return templates.TemplateResponse(request=request, name="reels.html", context={"factor": factor})


@risk_factor_router.get("/add")
def create_factor(request: Request):
    for factor in RISK_FACTORS:
        if is_risk_factor_drafted(factor):
            return templates.TemplateResponse(request=request, name="addition.html", context={"factor": factor})
