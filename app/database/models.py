from sqlalchemy import Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


class Segment(Base):
    """Un segment d'activite remonte par un agent."""

    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(String(255), nullable=False)
    employee_name: Mapped[str | None] = mapped_column(String(255))
    client: Mapped[str | None] = mapped_column(String(255))
    app: Mapped[str | None] = mapped_column(String(255))
    window_title: Mapped[str | None] = mapped_column(Text)
    project: Mapped[str | None] = mapped_column(String(255))
    version: Mapped[str | None] = mapped_column(String(50))
    state: Mapped[str | None] = mapped_column(String(20))
    start_ts: Mapped[str | None] = mapped_column(String(40))
    end_ts: Mapped[str | None] = mapped_column(String(40))
    duration_sec: Mapped[int | None] = mapped_column(Integer)
    received_at: Mapped[str | None] = mapped_column(String(40))

    __table_args__ = (
        UniqueConstraint(
            "employee_id", "start_ts", "app", "window_title", "state",
            name="uq_segment",
        ),
        Index("idx_emp", "employee_id"),
        Index("idx_start", "start_ts"),
    )


class AppSetting(Base):
    """Reglages centraux des agents (cle/valeur)."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text)
