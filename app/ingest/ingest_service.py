from app.ingest import ingest_repository


def ingest_events(batch):
    inserted = ingest_repository.insert_segments(batch.events)
    return {
        "status": "ok",
        "received": len(batch.events),
        "inserted": inserted,
    }
