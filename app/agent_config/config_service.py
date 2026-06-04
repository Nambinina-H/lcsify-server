from app.agent_config import config_repository
from app.agent_config.schemas import AgentConfig

# Valeurs par defaut (= la config livree si rien n'a ete enregistre).
DEFAULTS = AgentConfig().model_dump()


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
