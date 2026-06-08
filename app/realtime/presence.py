"""Présence en mémoire (temps réel) : qui fait quoi *maintenant*.

Alimentée par les heartbeats des agents (POST /api/heartbeat) et diffusée au
dashboard par SSE (GET /api/live). Volontairement en mémoire : pour une seule
instance serveur (cas actuel), c'est suffisant et sans dépendance (pas de Redis).
"""

import asyncio
import json
import threading
import time

_lock = threading.Lock()
_data: dict[str, dict] = {}
_version = 0
_ONLINE_WINDOW = 30  # secondes sans heartbeat -> considéré hors-ligne


def update(employee_id: str, fields: dict) -> None:
    """Met à jour la présence d'un monteur (appelé depuis le heartbeat)."""
    global _version
    if not employee_id:
        return
    with _lock:
        entry = _data.get(employee_id, {})
        entry.update({k: v for k, v in fields.items() if k != "employee_id"})
        entry["last_seen"] = time.time()
        _data[employee_id] = entry
        _version += 1


def snapshot():
    """(version, liste de présences) — `online` calculé selon la fraîcheur."""
    now = time.time()
    with _lock:
        version = _version
        items = []
        for eid, entry in _data.items():
            item = {k: v for k, v in entry.items() if k != "last_seen"}
            item["employee_id"] = eid
            item["online"] = (now - entry.get("last_seen", 0)) < _ONLINE_WINDOW
            items.append(item)
    return version, items


async def event_stream():
    """Flux SSE : pousse la présence à chaque changement, + un rafraîchissement
    périodique (~4 s) pour refléter les passages hors-ligne."""
    last_version = -1
    last_sent = 0.0
    while True:
        version, items = snapshot()
        now = time.monotonic()
        if version != last_version or (now - last_sent) >= 4:
            last_version = version
            last_sent = now
            yield f"data: {json.dumps({'presence': items})}\n\n"
        await asyncio.sleep(1.5)
