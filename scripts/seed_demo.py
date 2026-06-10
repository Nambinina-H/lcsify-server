"""Donnees de demonstration (injection / suppression faciles).

Schema relationnel : cree des employees / clients / projects / segments lies
par cles etrangeres. Les monteurs de demo ont un external_id suffixe ``@DEMO``,
ce qui permet une suppression ciblee sans toucher aux vraies donnees.

Usage (depuis le dossier server/, venv active) :
    python scripts/seed_demo.py seed     # injecte le jeu de demo
    python scripts/seed_demo.py clear    # supprime tout le jeu de demo

10 monteurs, 20 projets couvrant tous les cas d'avancement (non demarre,
en cours, presque fini, depasse, non estime), segments repartis sur les jours
precedents. Les journees demo suivent le rythme normal 9h-18h avec pause
inactive 13h-14h quand la journee depasse 4h actives. Ajoute aussi 5 projets
explicites aujourd'hui pour tester la frise : deux journees normales de 8h,
un petit depassement non marque, puis 1h et 2h d'heures supplementaires.
La sous-commande ``seed`` repart d'un etat propre (clear puis insert).
"""

import os
import random
import sys
from datetime import datetime, timedelta, timezone

# Rendre `app` importable quel que soit le repertoire d'appel.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import delete, select  # noqa: E402

from app.database.database_session import SessionLocal  # noqa: E402
from app.database.models import Client, Employee, Project, Segment  # noqa: E402

DEMO_SUFFIX = "@DEMO"
H = 3600

NAMES = [
    "Alice", "Bruno", "Chloe", "David", "Emma",
    "Farid", "Gina", "Hugo", "Ines", "Jules",
]
CLIENTS = [
    "Acme Corp", "Studio Nova", "Maison Belle", "Pixel Lab",
    "Orange Media", "Zenith Films", "BlueWave", "Karma Prod",
]
VIDEOS = [
    "Pub Ete 2026", "Clip Horizon", "Teaser Live", "Interview CEO",
    "Recap Event", "Spot Radio", "Aftermovie Gala", "Tuto Produit",
    "Motion Intro", "Docu Court", "Reels Campagne", "Best Of 2025",
    "Demo Reel", "Capsule RH", "Webserie Ep1", "Trailer Saison2",
    "Podcast Visio", "Annonce Produit", "Showreel Q2", "Clip Acoustique",
]
APPS = [
    "Adobe Premiere Pro", "Adobe After Effects", "DaVinci Resolve",
    "Adobe Audition", "Final Cut Pro",
]
OVERTIME_CASES = [
    {
        "client": "Acme Corp",
        "video": "Demo Normal 9h-18h",
        "version": "V1",
        "estimated": 8 * H,
        "emp_ext": f"alice{DEMO_SUFFIX}",
        "app": "Adobe Premiere Pro",
        "segments": [
            (0, 9, 0, 4 * H, "active"),
            (0, 13, 0, H, "idle"),
            (0, 14, 0, 4 * H, "active"),
        ],
    },
    {
        "client": "Studio Nova",
        "video": "Demo Normal Bis 9h-18h",
        "version": "V1",
        "estimated": 8 * H,
        "emp_ext": f"bruno{DEMO_SUFFIX}",
        "app": "DaVinci Resolve",
        "segments": [
            (0, 9, 0, 4 * H, "active"),
            (0, 13, 0, H, "idle"),
            (0, 14, 0, 4 * H, "active"),
        ],
    },
    {
        "client": "Maison Belle",
        "video": "Demo 9h Jusqu A 18h30",
        "version": "V1",
        "estimated": 8 * H,
        "emp_ext": f"chloe{DEMO_SUFFIX}",
        "app": "Adobe After Effects",
        "segments": [
            (0, 9, 0, 4 * H, "active"),
            (0, 13, 0, H, "idle"),
            (0, 14, 0, 4 * H, "active"),
            (0, 18, 0, 30 * 60, "active"),
        ],
    },
    {
        "client": "Pixel Lab",
        "video": "Demo 9h Jusqu A 19h",
        "version": "V1",
        "estimated": 8 * H,
        "emp_ext": f"david{DEMO_SUFFIX}",
        "app": "Final Cut Pro",
        "segments": [
            (0, 9, 0, 4 * H, "active"),
            (0, 13, 0, H, "idle"),
            (0, 14, 0, 4 * H, "active"),
            (0, 18, 0, H, "active"),
        ],
    },
    {
        "client": "Orange Media",
        "video": "Demo 9h Jusqu A 20h",
        "version": "V1",
        "estimated": 8 * H,
        "emp_ext": f"emma{DEMO_SUFFIX}",
        "app": "Adobe Premiere Pro",
        "segments": [
            (0, 9, 0, 4 * H, "active"),
            (0, 13, 0, H, "idle"),
            (0, 14, 0, 4 * H, "active"),
            (0, 18, 0, 2 * H, "active"),
        ],
    },
]


# Activite courte et fragmentee sur un jour "propre" (il y a 8 jours, non utilise
# par les autres donnees) -> plage horaire serree, beaucoup de mini-segments :
# sert a tester la frise du calendrier (zoom adaptatif + fusion des bandes).
ACT = "active"
IDL = "idle"
SHORT_DAYS_BACK = 8
SHORT_CASES = [
    {"client": "Acme Corp", "video": "Court Demo A", "emp_ext": f"alice{DEMO_SUFFIX}",
     "app": "Adobe Premiere Pro", "hour": 14, "minute": 0,
     "pattern": [(ACT, 3), (ACT, 2), (IDL, 1), (ACT, 4), (ACT, 3), (IDL, 2), (ACT, 2)]},
    {"client": "Studio Nova", "video": "Court Demo B", "emp_ext": f"bruno{DEMO_SUFFIX}",
     "app": "DaVinci Resolve", "hour": 14, "minute": 6,
     "pattern": [(ACT, 5), (IDL, 1), (ACT, 4), (ACT, 3), (IDL, 1), (ACT, 4)]},
    {"client": "Maison Belle", "video": "Court Demo C", "emp_ext": f"chloe{DEMO_SUFFIX}",
     "app": "Adobe After Effects", "hour": 14, "minute": 2,
     "pattern": [(ACT, 6), (ACT, 5), (IDL, 2), (ACT, 7), (ACT, 6), (IDL, 1), (ACT, 5), (ACT, 5)]},
    {"client": "Pixel Lab", "video": "Court Demo D", "emp_ext": f"david{DEMO_SUFFIX}",
     "app": "Final Cut Pro", "hour": 14, "minute": 10,
     "pattern": [(ACT, 4), (ACT, 3), (ACT, 2), (IDL, 1), (ACT, 3), (ACT, 2)]},
    {"client": "Orange Media", "video": "Court Demo E", "emp_ext": f"emma{DEMO_SUFFIX}",
     "app": "Adobe Audition", "hour": 14, "minute": 4,
     "pattern": [(ACT, 8), (IDL, 2), (ACT, 9), (ACT, 6), (IDL, 1), (ACT, 10)]},
    {"client": "Zenith Films", "video": "Court Demo F", "emp_ext": f"farid{DEMO_SUFFIX}",
     "app": "Adobe Premiere Pro", "hour": 14, "minute": 8,
     "pattern": [(ACT, 4), (ACT, 4), (IDL, 1), (ACT, 5), (ACT, 4), (IDL, 1), (ACT, 3)]},
]


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _build_projects():
    """20 tuples projet deterministes. Chaque monteur recoit 2 projets aux
    avancements differents -> tout le monde a du travail mesure."""
    random.seed(7)
    ext_ids = [f"{n.lower()}{DEMO_SUFFIX}" for n in NAMES]
    projects = []
    for i in range(20):
        emp_ext = ext_ids[i // 2]  # 2 projets consecutifs par monteur
        client = CLIENTS[i % len(CLIENTS)]
        video = VIDEOS[i]
        version = f"V{(i % 6) + 1}"
        app = APPS[i % len(APPS)]
        start_hour = 9

        non_estimated = i % 7 == 0
        estimated = 0 if non_estimated else random.choice([1, 2, 3, 4, 5, 6, 8]) * H

        bucket = i % 5
        if non_estimated:
            realised = random.choice([1, 2, 3]) * H + random.randint(0, 40) * 60
        elif bucket == 0:
            realised = 0  # non demarre
        elif bucket == 1:
            realised = int(estimated * random.uniform(1.1, 1.4))  # depasse
        elif bucket == 2:
            realised = int(estimated * random.uniform(0.85, 0.98))  # presque fini
        elif bucket == 3:
            realised = int(estimated * random.uniform(0.4, 0.6))  # a mi-parcours
        else:
            realised = int(estimated * random.uniform(0.1, 0.25))  # a peine commence

        n_days = random.randint(2, 4) if realised > 0 else 0
        days = sorted(random.sample(range(1, 8), n_days)) if n_days else []
        projects.append(
            (client, video, version, estimated, emp_ext, realised, app, days, start_hour)
        )
    return projects


def _segments_for(project_id, employee_id, app, video, realised, days, start_hour, now):
    if realised <= 0 or not days:
        return []
    base = realised // len(days)
    rem = realised - base * len(days)
    rows = []
    for i, days_back in enumerate(days):
        active = base + (rem if i == 0 else 0)
        day = now - timedelta(days=days_back)
        title = f"{video} - {app}"

        def add_segment(state, started_at, duration):
            if duration <= 0:
                return
            rows.append({
                "employee_id": employee_id, "project_id": project_id,
                "app": app, "window_title": title, "state": state,
                "started_at": started_at,
                "ended_at": started_at + timedelta(seconds=duration),
                "duration_sec": duration,
                "received_at": now,
            })

        remaining = active
        morning_start = day.replace(
            hour=start_hour, minute=0, second=0, microsecond=0
        )
        morning = min(remaining, 4 * H)
        add_segment("active", morning_start, morning)
        remaining -= morning

        if remaining > 0:
            pause_start = day.replace(hour=13, minute=0, second=0, microsecond=0)
            add_segment("idle", pause_start, H)

            afternoon_start = day.replace(hour=14, minute=0, second=0, microsecond=0)
            afternoon = min(remaining, 4 * H)
            add_segment("active", afternoon_start, afternoon)
            remaining -= afternoon

        if remaining > 0:
            overtime_start = day.replace(hour=18, minute=0, second=0, microsecond=0)
            add_segment("active", overtime_start, remaining)
    return rows


def _fixed_segments_for(project_id, employee_id, app, video, intervals, now):
    """Segments explicites pour tester les heures sup dans le calendrier.

    interval = (days_back, hour, minute, duration_sec[, state])
    """
    rows = []
    title = f"{video} - {app}"
    for interval in intervals:
        days_back, hour, minute, duration, *maybe_state = interval
        state = maybe_state[0] if maybe_state else "active"
        day = now - timedelta(days=days_back)
        start = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
        end = start + timedelta(seconds=duration)
        rows.append({
            "employee_id": employee_id, "project_id": project_id,
            "app": app, "window_title": title, "state": state,
            "started_at": start, "ended_at": end,
            "duration_sec": duration, "received_at": now,
        })
    return rows


def _fragmented_segments(project_id, employee_id, app, video, hour, minute, pattern, now):
    """Segments consecutifs (actif/inactif) poses bout a bout depuis hour:minute,
    sur le jour SHORT_DAYS_BACK. pattern = liste de (state, minutes)."""
    rows = []
    title = f"{video} - {app}"
    day = now - timedelta(days=SHORT_DAYS_BACK)
    cursor = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
    for state, minutes in pattern:
        dur = minutes * 60
        end = cursor + timedelta(seconds=dur)
        rows.append({
            "employee_id": employee_id, "project_id": project_id,
            "app": app, "window_title": title, "state": state,
            "started_at": cursor, "ended_at": end,
            "duration_sec": dur, "received_at": now,
        })
        cursor = end
    return rows


def clear():
    with SessionLocal() as session:
        demo_ids = [
            r[0] for r in session.execute(
                select(Employee.id).where(Employee.external_id.like(f"%{DEMO_SUFFIX}"))
            ).all()
        ]
        seg = proj = 0
        if demo_ids:
            seg = session.execute(
                delete(Segment).where(Segment.employee_id.in_(demo_ids))
            ).rowcount
            proj = session.execute(
                delete(Project).where(Project.assigned_employee_id.in_(demo_ids))
            ).rowcount
        # Clients du jeu de demo devenus orphelins (plus aucun projet).
        cli = session.execute(
            delete(Client).where(
                Client.name.in_(CLIENTS),
                Client.id.notin_(select(Project.client_id)),
            )
        ).rowcount
        emp = session.execute(
            delete(Employee).where(Employee.external_id.like(f"%{DEMO_SUFFIX}"))
        ).rowcount
        session.commit()
    print(
        f"Supprime : {seg or 0} segments, {proj or 0} projets, "
        f"{cli or 0} clients, {emp or 0} monteurs (demo)."
    )


def seed():
    clear()  # repart d'un etat propre -> idempotent
    now = _now()
    with SessionLocal() as session:
        emp_ids = {}
        for n in NAMES:
            ext = f"{n.lower()}{DEMO_SUFFIX}"
            emp = Employee(external_id=ext, name=f"{n} Demo")
            session.add(emp)
            session.flush()
            emp_ids[ext] = emp.id

        client_ids = {}

        def client_id(name):
            if name not in client_ids:
                existing = session.execute(
                    select(Client).where(Client.name == name)
                ).scalar_one_or_none()
                if existing is None:
                    existing = Client(name=name)
                    session.add(existing)
                    session.flush()
                client_ids[name] = existing.id
            return client_ids[name]

        n_proj = n_seg = 0
        for p in _build_projects():
            (client, video, version, estimated, emp_ext, realised, app, days, hour) = p
            project = Project(
                client_id=client_id(client),
                video_name=video,
                version=version,
                estimated_duration_sec=estimated,
                assigned_employee_id=emp_ids[emp_ext],
            )
            session.add(project)
            session.flush()
            n_proj += 1
            for row in _segments_for(
                project.id, emp_ids[emp_ext], app, video, realised, days, hour, now
            ):
                session.add(Segment(**row))
                n_seg += 1

        for case in OVERTIME_CASES:
            project = Project(
                client_id=client_id(case["client"]),
                video_name=case["video"],
                version=case["version"],
                estimated_duration_sec=case["estimated"],
                assigned_employee_id=emp_ids[case["emp_ext"]],
            )
            session.add(project)
            session.flush()
            n_proj += 1
            for row in _fixed_segments_for(
                project.id,
                emp_ids[case["emp_ext"]],
                case["app"],
                case["video"],
                case["segments"],
                now,
            ):
                session.add(Segment(**row))
                n_seg += 1

        for case in SHORT_CASES:
            project = Project(
                client_id=client_id(case["client"]),
                video_name=case["video"],
                version="V1",
                estimated_duration_sec=30 * 60,
                assigned_employee_id=emp_ids[case["emp_ext"]],
            )
            session.add(project)
            session.flush()
            n_proj += 1
            for row in _fragmented_segments(
                project.id,
                emp_ids[case["emp_ext"]],
                case["app"],
                case["video"],
                case["hour"],
                case["minute"],
                case["pattern"],
                now,
            ):
                session.add(Segment(**row))
                n_seg += 1
        session.commit()
    print(f"Injecte : {len(NAMES)} monteurs, {n_proj} projets, {n_seg} segments (demo).")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "seed":
        seed()
    elif cmd == "clear":
        clear()
    else:
        print("Usage: python scripts/seed_demo.py [seed|clear]")
        sys.exit(1)


if __name__ == "__main__":
    main()
