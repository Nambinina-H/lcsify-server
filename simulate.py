"""Genere des donnees de test pour 16 monteurs sur 7 jours et les envoie au serveur."""
import random
import requests
from datetime import datetime, timezone, timedelta

API = "http://127.0.0.1:8000/api/events"
KEY = "test-key"

APPS = {
    "Adobe Premiere Pro.exe": [".prproj", ["Pub Nike", "Mariage Rakoto", "Doc YouTube"]],
    "AfterFX.exe":            [".aep",    ["Pub Nike", "Intro Chaine"]],
    "Resolve.exe":            [".drp",    ["Clip Musical", "Doc YouTube"]],
    "chrome.exe":             [None,      ["YouTube", "Gmail", "Drive"]],
    "explorer.exe":           [None,      None],
}
NAMES = ["Rakoto J.","Rabe M.","Hery N.","Tina R.","Lova S.","Naina T.","Faly H.",
         "Mamy V.","Diary L.","Tojo R.","Sitraka A.","Onja P.","Miora K.","Fanja D.",
         "Tahiry B.","Ny Aina F."]

def iso(dt): return dt.replace(tzinfo=timezone.utc).isoformat()

batch = []
now = datetime.utcnow()
for i, name in enumerate(NAMES):
    emp_id = f"monteur-{i+1:02d}"
    # profil d'assiduite variable selon le monteur
    diligence = random.uniform(0.45, 0.95)
    for d in range(7):
        day = now - timedelta(days=d)
        cursor = day.replace(hour=8, minute=0, second=0, microsecond=0)
        end_day = day.replace(hour=17, minute=0, second=0, microsecond=0)
        while cursor < end_day:
            active = random.random() < diligence
            dur = random.randint(2, 25) * 60
            if active:
                app = random.choices(list(APPS), weights=[5,3,3,4,1])[0]
                ext, projs = APPS[app]
                project = None
                title = app
                if projs:
                    proj = random.choice(projs)
                    project = proj + (ext if ext else "")
                    title = f"{proj}{ext or ''} - {app}"
                batch.append(dict(employee_id=emp_id, employee_name=name, app=app,
                    window_title=title, project=project, state="active",
                    start_ts=iso(cursor), end_ts=iso(cursor+timedelta(seconds=dur)),
                    duration_sec=dur))
            else:
                batch.append(dict(employee_id=emp_id, employee_name=name, app="(inactif)",
                    window_title="", project=None, state="idle",
                    start_ts=iso(cursor), end_ts=iso(cursor+timedelta(seconds=dur)),
                    duration_sec=dur))
            cursor += timedelta(seconds=dur)

print(f"{len(batch)} segments generes pour {len(NAMES)} monteurs.")
# envoi par paquets
for j in range(0, len(batch), 500):
    chunk = batch[j:j+500]
    r = requests.post(API, json={"events": chunk}, headers={"X-API-Key": KEY}, timeout=30)
    r.raise_for_status()
print("Envoi termine.")
