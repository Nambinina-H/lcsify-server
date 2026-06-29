from datetime import date

from pydantic import BaseModel, Field

# Types de demande (cles stables ; libelles cote front).
LEAVE_TYPES = ("permission", "conge_paye", "sans_solde", "autre")
PAID_TYPE = "conge_paye"          # seul type qui decompte le solde
# Statuts (Phase 1 : saisie RH directe = approuve ; Phase 2 : validation).
LEAVE_STATUSES = ("en_attente", "approuve", "refuse")


class HrCollaborateurIn(BaseModel):
    """Fiche RH (registre des conges). Cle metier = matricule."""

    matricule: str = Field(min_length=1, max_length=50)
    nom: str | None = None
    prenom: str | None = None
    solde_initial: float = 0
    date_solde: date | None = None
    poste: str | None = None
    service: str | None = None


class LeaveIn(BaseModel):
    """Conge / absence. nb_jours None -> calcule (jours calendaires inclus).

    Le statut n'est PAS dans ce payload : une demande est creee « en attente »
    puis validee/refusee depuis le tableau (LeaveStatusIn)."""

    hr_id: int
    type: str = "conge_paye"
    date_debut: date
    date_fin: date
    nb_jours: float | None = None
    motif: str | None = None
    validateur: str | None = None  # validateur designe (affiche dans le tableau)


class LeaveStatusIn(BaseModel):
    """Validation d'un conge depuis le tableau : en_attente | approuve | refuse."""

    statut: str


class HrLinkIn(BaseModel):
    """Rattache un collaborateur (agent) a une fiche RH. None = detache."""

    hr_collaborateur_id: int | None = None
