from typing import Final

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from models.risk_factors import RISK_FACTORS, is_risk_factor_published, is_risk_factor_weight_bigger

TEMPLATES_PATH: Final[str] = "../FRAX-frontend/templates"

frax_router = APIRouter(tags=["frax"])
templates = Jinja2Templates(TEMPLATES_PATH)


@frax_router.get("/")
def get_risk_factors(request: Request, risk_factor_weight: float | None = None):
    if risk_factor_weight is None:
        return templates.TemplateResponse(request=request, name="index.html", context={"risk_factors": RISK_FACTORS})

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "risk_factors": [
                risk_factor
                for risk_factor in RISK_FACTORS
                if is_risk_factor_weight_bigger(risk_factor, risk_factor_weight) and is_risk_factor_published(risk_factor)
            ]
        },
    )
