from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
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


class Space(Base, TimestampMixin):
    """Espace : categorie de collaborateurs (Monteurs, Marketing, Dev...). Le
    dashboard se filtre par espace ; un collaborateur appartient a un seul espace
    (Employee.space_id). Couleur + icone pour le selecteur de la sidebar."""

    __tablename__ = "spaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    color: Mapped[str] = mapped_column(String(20), nullable=False, server_default="#1d4ed8")
    icon: Mapped[str] = mapped_column(String(40), nullable=False, server_default="grid")


class Employee(Base, TimestampMixin):
    """Monteur (registre central). external_id = identite machine 'user@host'."""

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str | None] = mapped_column(String(100))  # metier (Monteur, ...)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Espace d'appartenance (categorie). NULL = non classe. SET NULL si l'espace
    # est supprime (le collaborateur et son historique restent intacts).
    space_id: Mapped[int | None] = mapped_column(
        ForeignKey("spaces.id", ondelete="SET NULL"), index=True
    )
    # Fiche RH reliee (registre des conges). NULL = non relie. SET NULL si la
    # fiche est supprimee. C'est ce lien qui rattache un collaborateur (agent) a
    # son solde de conges et a ses demandes.
    hr_collaborateur_id: Mapped[int | None] = mapped_column(
        ForeignKey("hr_collaborateurs.id", ondelete="SET NULL"), index=True
    )


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


class HrCollaborateur(Base, TimestampMixin):
    """Fiche RH (registre des conges), importee du fichier du RH. Cle = matricule.

    Le solde de conges est calcule a la lecture :
        solde_initial + 2,5 j par fin de mois ecoulee depuis date_solde
        - conges payes approuves.
    Un collaborateur (agent) peut etre relie a une fiche via
    Employee.hr_collaborateur_id (les noms agent/RH ne correspondent pas : le
    rapprochement est fait manuellement par le RH)."""

    __tablename__ = "hr_collaborateurs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    matricule: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nom: Mapped[str | None] = mapped_column(String(255))
    prenom: Mapped[str | None] = mapped_column(String(255))
    # Solde de reference (jours) tel que fourni dans le fichier RH.
    solde_initial: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0"
    )
    # Date de reference du solde : le +2,5 j/mois part de la.
    date_solde: Mapped[date | None] = mapped_column(Date)
    poste: Mapped[str | None] = mapped_column(String(255))
    service: Mapped[str | None] = mapped_column(String(255))


class Leave(Base, TimestampMixin):
    """Conge / absence d'un collaborateur (relie a une fiche RH par hr_id).

    nb_jours = jours CALENDAIRES (week-ends compris : les contrats sont payes
    tous les jours du mois). Seul le conge paye (type='conge_paye') decompte le
    solde. statut : 'approuve' (saisie RH directe, Phase 1) ; le champ est pret
    pour la validation des demandes (Phase 2 : 'en_attente' -> 'approuve'/'refuse')."""

    __tablename__ = "leaves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hr_id: Mapped[int] = mapped_column(
        ForeignKey("hr_collaborateurs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin: Mapped[date] = mapped_column(Date, nullable=False)
    nb_jours: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    motif: Mapped[str | None] = mapped_column(Text)
    statut: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="approuve"
    )
    created_by: Mapped[str | None] = mapped_column(String(255))  # nom (snapshot)
    # Validateur DÉSIGNÉ à la création (saisi dans le formulaire) : affiché dans
    # le tableau. Distinct de decided_by (qui a réellement validé -> historique).
    validateur: Mapped[str | None] = mapped_column(String(255))
    # Qui a change le statut en dernier (validation / refus) + quand. Affiché
    # uniquement dans l'historique (audit), pas dans le tableau des congés.
    decided_by: Mapped[str | None] = mapped_column(String(255))  # nom (snapshot)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime)


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
