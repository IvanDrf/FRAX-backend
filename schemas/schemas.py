from pydantic import BaseModel, Field

from models.risk_factor import FactorCategory


class CreateRiskFactorSchema(BaseModel):
    name: str
    description: str | None
    weight: float = Field(ge=0)
    prevalence: int | None = None
    category: FactorCategory
