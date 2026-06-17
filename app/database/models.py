from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import RoleEnum
from app.database.database import Base


class TimestampMixin:
    """Colonnes d'audit communes (cree / mis a jour)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(Base, TimestampMixin):
    """Compte manager du dashboard (authentification JWT)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RoleEnum.MANAGER.value
    )
    # Permissions additionnelles (au-dela du role) : JSON, ex. ["history:view"].
    scopes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Employee(Base, TimestampMixin):
    """Monteur (registre central). external_id = identite machine 'user@host'."""

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str | None] = mapped_column(String(100))  # metier (Monteur, ...)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Client(Base, TimestampMixin):
    """Client (label normalise, reutilise par les projets)."""

    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)


class Project(Base, TimestampMixin):
    """Livrable : client + nom de video + version, avec temps prevu et monteur."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    video_name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    estimated_duration_sec: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    assigned_employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL")
    )
    # Statut du livrable : "en_cours" (defaut) ou "termine" (marque par un manager
    # ou par le monteur depuis l'agent). + qui l'a termine et quand.
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="en_cours"
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_by: Mapped[str | None] = mapped_column(String(255))
    # Nom (snapshot) de l'utilisateur qui a cree le projet.
    created_by: Mapped[str | None] = mapped_column(String(255))
    # Priorite pour le collaborateur assigne : 1 = plus prioritaire ; 0 = non
    # priorise (classe en dernier). Ordonne la liste affichee dans l'agent.
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    client = relationship("Client")
    employee = relationship("Employee")

    __table_args__ = (
        UniqueConstraint(
            "client_id", "video_name", "version",
            name="uq_project_client_video_version",
        ),
        Index("idx_project_client", "client_id"),
        Index("idx_project_employee", "assigned_employee_id"),
    )


class Segment(Base):
    """Un segment d'activite remonte par un agent (lie au monteur et au projet)."""

    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL")
    )
    app: Mapped[str | None] = mapped_column(String(255))
    window_title: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str | None] = mapped_column(String(20))
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    duration_sec: Mapped[int | None] = mapped_column(Integer)
    # Clics souris du segment (APM). Nullable : les anciens agents n'en envoient
    # pas -> NULL traite comme 0 dans les calculs.
    clicks: Mapped[int | None] = mapped_column(Integer, server_default="0")
    received_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Pas de relationship() ici : les rapports font des jointures explicites.
    # Le lien en base reste assure par les ForeignKey ci-dessus.

    __table_args__ = (
        UniqueConstraint(
            "employee_id", "started_at", "app", "window_title", "state",
            name="uq_segment",
        ),
        Index("idx_seg_emp", "employee_id"),
        Index("idx_seg_start", "started_at"),
        Index("idx_seg_project", "project_id"),
    )


class AppSetting(Base):
    """Reglages centraux des agents (cle/valeur)."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text)


class AuditLog(Base):
    """Journal d'audit : qui a fait quoi sur la plateforme (historique)."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    user_label: Mapped[str | None] = mapped_column(String(255))  # nom fige (snapshot)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # ex. project.create
    summary: Mapped[str] = mapped_column(Text, nullable=False)  # phrase lisible (FR)
    details: Mapped[str | None] = mapped_column(Text)  # JSON optionnel
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_audit_created", "created_at"),
        Index("idx_audit_action", "action"),
    )
