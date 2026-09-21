from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Like(Base):
    __tablename__ = "likes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    risk_factor_id: Mapped[int] = mapped_column(Integer, ForeignKey("risk_factors.id"), nullable=False)
