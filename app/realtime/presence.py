"""Présence en mémoire (temps réel) : qui fait quoi *maintenant*.

Alimentée par les heartbeats des agents (POST /api/heartbeat) et diffusée au
dashboard par SSE (GET /api/live). Volontairement en mémoire : pour une seule
instance serveur (cas actuel), c'est suffisant et sans dépendance (pas de Redis).

Le passage hors-ligne est explicite (l'agent envoie `state="offline"` à la
fermeture) ; le TTL ci-dessous n'est qu'un filet de sécurité (crash, coupure
réseau) si ce signal n'arrive jamais.
"""

import asyncio
import json
import threading
import time

_lock = threading.Lock()
_data: dict[str, dict] = {}
_version = 0
_ONLINE_WINDOW = 25  # secondes sans signal -> hors-ligne (filet de sécurité)


def update(employee_id: str, fields: dict) -> None:
    """Met à jour la présence d'un monteur (heartbeat normal)."""
    global _version
    if not employee_id:
        return
    with _lock:
        entry = _data.get(employee_id, {})
        entry.update({k: v for k, v in fields.items() if k != "employee_id"})
        entry["last_seen"] = time.time()
        entry["_offline"] = False
        _data[employee_id] = entry
        _version += 1


def mark_offline(employee_id: str) -> None:
    """Passe un monteur hors-ligne tout de suite (fermeture/arrêt de l'agent)."""
    global _version
    if not employee_id:
        return
    with _lock:
        entry = _data.get(employee_id)
        if entry is None:
            entry = {}
            _data[employee_id] = entry
        entry["_offline"] = True
        _version += 1


def snapshot():
    """(version, liste de présences) — `online` selon signal + fraîcheur."""
    now = time.time()
    with _lock:
        version = _version
        items = []
        for eid, entry in _data.items():
            online = (not entry.get("_offline")) and (
                now - entry.get("last_seen", 0) < _ONLINE_WINDOW
            )
            item = {
                k: v for k, v in entry.items() if k not in ("last_seen", "_offline")
            }
            item["employee_id"] = eid
            item["online"] = online
            items.append(item)
    return version, items


async def event_stream():
    """Flux SSE : pousse la présence à chaque changement (≤1 s), + un
    rafraîchissement périodique (~3 s) pour refléter les expirations TTL."""
    last_version = -1
    last_sent = 0.0
    while True:
        version, items = snapshot()
        now = time.monotonic()
        if version != last_version or (now - last_sent) >= 3:
            last_version = version
            last_sent = now
            yield f"data: {json.dumps({'presence': items})}\n\n"
        await asyncio.sleep(1)
