from datetime import datetime, timedelta, timezone
from enum import Enum

from sqlalchemy import TIMESTAMP, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ENUM as PostgreSQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class FactorCategory(Enum):
    BINARY = "Бинарный"
    NUMERIC = "Числовой"
    CATEGORICAL = "Категориальный"


class PublicationStatus(Enum):
    PUBLISHED = "published"
    DRAFT = "draft"
    DELETED = "deleted"


class RiskFactor(Base):
    __tablename__ = "risk_factors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)

    weight: Mapped[float] = mapped_column(Float, default=1, nullable=True)
    prevalence: Mapped[int] = mapped_column(Integer, nullable=True)
    category: Mapped[FactorCategory] = mapped_column(
        PostgreSQLEnum(
            FactorCategory,
            name="factor_category",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        default=FactorCategory.CATEGORICAL,
        nullable=False,
    )
    publication_status: Mapped[PublicationStatus] = mapped_column(
        PostgreSQLEnum(
            PublicationStatus,
            name="publication_status",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        default=PublicationStatus.DRAFT,
        nullable=False,
    )

    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.now(timezone(offset=timedelta(hours=3))), nullable=False
    )
    formated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
