from app.agent_config import config_repository
from app.agent_config.schemas import AgentConfig

# Valeurs par defaut (= la config livree si rien n'a ete enregistre).
DEFAULTS = AgentConfig().model_dump()

# Compteur "top de mise a jour" : incremente quand un admin demande une MAJ
# immediate de la flotte ; chaque agent declenche son telechargement quand il
# voit ce nombre augmenter. Hors du schema config (jamais ecrase par un PUT).
_UPDATE_SIGNAL_KEY = "update_signal"


def get_config():
    """Config courante : valeurs enregistrees fusionnees sur les defauts."""
    stored = config_repository.get_all()
    data = dict(DEFAULTS)
    for key in DEFAULTS:
        if key in stored:
            try:
                data[key] = int(stored[key])
            except (TypeError, ValueError):
                pass
    return data


def update_config(payload: AgentConfig):
    """Enregistre la config (deja validee/bornee par le schema) et la renvoie."""
    config_repository.set_many(payload.model_dump())
    return get_config()


def get_update_signal():
    """Valeur courante du compteur de MAJ (0 si jamais declenche)."""
    stored = config_repository.get_all()
    try:
        return int(stored.get(_UPDATE_SIGNAL_KEY, 0))
    except (TypeError, ValueError):
        return 0


def bump_update_signal():
    """Incremente le compteur -> les agents declencheront leur MAJ a la prochaine
    lecture de config (~60 s). Renvoie la nouvelle valeur."""
    new = get_update_signal() + 1
    config_repository.set_many({_UPDATE_SIGNAL_KEY: new})
    return new


def get_agent_payload():
    """Config envoyee aux agents : reglages + top de mise a jour."""
    cfg = get_config()
    cfg[_UPDATE_SIGNAL_KEY] = get_update_signal()
    return cfg
