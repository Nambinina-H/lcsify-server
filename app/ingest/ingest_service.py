from app.ingest import ingest_repository


def ingest_events(batch):
    inserted = ingest_repository.insert_segments(batch.events, batch.client_sent_at)
    return {
        "status": "ok",
        "received": len(batch.events),
        "inserted": inserted,
    }
