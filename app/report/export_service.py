"""Export Excel (.xlsx) du calendrier — grille hebdo type Clockify, par mois.

Par agent : lignes = sa plage horaire perso (debut d'activite -> +9h, en heure
locale), colonnes = jours ouvres (Lun-Ven) regroupes par semaine sur tout le
mois. Chaque case = tous les projets captures cette heure-la (listes), couleur =
version dominante (V1/V2/V3/Autres), rouge si depassement du temps prevu.
Les statuts manuels (conge, attente, absence...) ne sont pas geres (non captures)
-> cases laissees vides. Heures en local Madagascar (UTC+3).
"""
import calendar as _cal
from datetime import date, datetime, timedelta
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import select

from app.common.enums import StateEnum
from app.database.database_session import SessionLocal
from app.database.models import Employee, Project, Segment, Space

_ACTIVE = StateEnum.ACTIVE.value
_LOCAL_OFFSET = timedelta(hours=3)   # Madagascar UTC+3
_HOURS_SPAN = 10                     # nb de lignes d'heures par agent (debut -> +9)
_DEFAULT_START = 9                   # plage par defaut si aucune activite

# Teintes proches du PDF (hex sans '#').
_FILL = {
    "V1": "DCE9FB",      # bleu clair
    "V2": "FCE5D6",      # orange clair
    "V3": "E6DCF2",      # violet clair
    "AUTRES": "EAEAEA",  # gris
    "OVER": "F6C6C2",    # rouge clair (depassement)
}
_DAYS = ["Lun", "Mar", "Mer", "Jeu", "Ven"]
_MONTHS = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet",
           "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
_NAVY = "0E2638"


def _gather(year, month, space_id):
    last_day = _cal.monthrange(year, month)[1]
    lo = datetime(year, month, 1) - _LOCAL_OFFSET           # bornes locales -> UTC
    hi = datetime(year, month, last_day, 23, 59, 59) - _LOCAL_OFFSET
    with SessionLocal() as s:
        space = s.get(Space, space_id) if space_id else None
        emp_q = select(Employee.id, Employee.external_id, Employee.name).where(
            Employee.is_active.is_(True))
        if space_id is not None:
            emp_q = emp_q.where(Employee.space_id == space_id)
        employees = [
            {"id": r.id, "name": r.name or r.external_id}
            for r in s.execute(emp_q.order_by(Employee.name)).all()
        ]
        segs = s.execute(
            select(
                Segment.employee_id, Segment.project_id,
                Segment.started_at, Segment.ended_at, Segment.duration_sec,
                Project.video_name, Project.version,
                Project.estimated_duration_sec,
            )
            .join(Project, Segment.project_id == Project.id)
            .where(Segment.state == _ACTIVE,
                   Segment.started_at >= lo, Segment.started_at <= hi)
        ).all()
        # Depassement : temps actif total (toutes periodes) > temps prevu.
        spent = {}
        for r in s.execute(
            select(Segment.project_id, Segment.duration_sec).where(
                Segment.state == _ACTIVE, Segment.project_id.is_not(None))
        ).all():
            spent[r.project_id] = spent.get(r.project_id, 0) + (r.duration_sec or 0)
    est = {r.project_id: (r.estimated_duration_sec or 0) for r in segs}
    overbudget = {pid for pid, e in est.items() if e > 0 and spent.get(pid, 0) > e}
    return space, employees, segs, overbudget


def _bucket(segs):
    """cells[(emp_id, date, hour)][label] = {sec, first, version, pid}."""
    cells = {}
    for r in segs:
        start = r.started_at + _LOCAL_OFFSET
        end = (r.ended_at + _LOCAL_OFFSET) if r.ended_at else (
            start + timedelta(seconds=r.duration_sec or 0))
        if end <= start:
            end = start + timedelta(seconds=max(r.duration_sec or 0, 1))
        cur = start
        while cur < end:
            seg_end = min(end, cur.replace(minute=0, second=0, microsecond=0)
                          + timedelta(hours=1))
            key = (r.employee_id, cur.date(), cur.hour)
            cell = cells.setdefault(key, {}).setdefault(
                r.video_name,
                {"sec": 0.0, "first": cur, "version": r.version, "pid": r.project_id},
            )
            cell["sec"] += (seg_end - cur).total_seconds()
            if cur < cell["first"]:
                cell["first"] = cur
            cur = seg_end
    return cells


def _week_blocks(year, month):
    """[(num_semaine, [(date, dans_le_mois) x5 Lun..Ven]), ...] pour le mois."""
    last = _cal.monthrange(year, month)[1]
    weeks = {}
    for day in range(1, last + 1):
        d = date(year, month, day)
        if d.weekday() < 5:
            iso = d.isocalendar()
            weeks[(iso[0], iso[1])] = True
    blocks = []
    for iy, iw in sorted(weeks):
        monday = date.fromisocalendar(iy, iw, 1)
        days = [(monday + timedelta(days=i),
                 (monday + timedelta(days=i)).month == month
                 and (monday + timedelta(days=i)).year == year)
                for i in range(5)]
        blocks.append((iw, days))
    return blocks


def build_calendar_xlsx(year, month, space_id=None):
    space, employees, segs, overbudget = _gather(year, month, space_id)
    cells = _bucket(segs)
    blocks = _week_blocks(year, month)

    wb = Workbook()
    ws = wb.active
    ws.title = (_MONTHS[month] or "Export")[:31]

    thin = Side(style="thin", color="D0D5DB")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left = Alignment(horizontal="left", vertical="top", wrap_text=True)
    head_fill = PatternFill("solid", fgColor=_NAVY)
    head_font = Font(color="FFFFFF", bold=True, size=10)
    agent_fill = PatternFill("solid", fgColor="F1F4F7")
    out_fill = PatternFill("solid", fgColor="F7F8FA")  # jour hors mois

    last_col = 2 + 5 * len(blocks)
    espace = f" — Espace {space.name}" if space else " — Tous"
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=last_col)
    t = ws.cell(1, 1, f"Suivi du temps — {_MONTHS[month]} {year}{espace}")
    t.font = Font(bold=True, size=13, color=_NAVY)

    ROW_WEEK, ROW_DAY = 2, 3
    for col, label in ((1, "Agent"), (2, "Heure")):
        c = ws.cell(ROW_DAY, col, label)
        c.font = head_font; c.fill = head_fill; c.alignment = center; c.border = border
    col = 3
    for iw, days in blocks:
        ws.merge_cells(start_row=ROW_WEEK, start_column=col, end_row=ROW_WEEK,
                       end_column=col + 4)
        wc = ws.cell(ROW_WEEK, col, f"Semaine {iw}")
        wc.font = head_font; wc.fill = head_fill; wc.alignment = center
        for i, (dd, in_month) in enumerate(days):
            hc = ws.cell(ROW_DAY, col + i, f"{_DAYS[i]} {dd.day:02d}" if in_month else "")
            hc.font = head_font; hc.fill = head_fill; hc.alignment = center
            hc.border = border
        col += 5

    row = ROW_DAY + 1
    for emp in employees:
        hours = [h for (eid, _d, h) in cells if eid == emp["id"]]
        start = min(hours) if hours else _DEFAULT_START
        end = min(max(max(hours), start + _HOURS_SPAN - 1) if hours
                  else start + _HOURS_SPAN - 1, 23)
        hour_list = list(range(start, end + 1))
        block_start, block_end = row, row + len(hour_list) - 1

        ws.merge_cells(start_row=block_start, start_column=1,
                       end_row=block_end, end_column=1)
        ac = ws.cell(block_start, 1, emp["name"])
        ac.alignment = center; ac.fill = agent_fill
        ac.font = Font(bold=True, size=10, color=_NAVY)

        for idx, hour in enumerate(hour_list):
            r = block_start + idx
            hcell = ws.cell(r, 2, f"{hour:02d}h")
            hcell.alignment = center; hcell.border = border
            hcell.font = Font(size=9, color="6C7884")
            col = 3
            for iw, days in blocks:
                for i, (dd, in_month) in enumerate(days):
                    cc = ws.cell(r, col + i)
                    cc.alignment = left; cc.border = border
                    if not in_month:
                        cc.fill = out_fill
                        continue
                    bucket = cells.get((emp["id"], dd, hour))
                    if not bucket:
                        continue
                    items = sorted(bucket.items(), key=lambda kv: kv[1]["first"])
                    cc.value = "\n".join(lbl for lbl, _ in items)
                    dom = max(bucket.values(), key=lambda v: v["sec"])
                    color = (_FILL["OVER"] if dom["pid"] in overbudget
                             else _FILL.get((dom["version"] or "").upper(),
                                            _FILL["AUTRES"]))
                    cc.fill = PatternFill("solid", fgColor=color)
                col += 5

        # Fusion verticale des heures consecutives identiques (par colonne jour).
        for c_idx in range(3, last_col + 1):
            rr = block_start
            while rr <= block_end:
                val = ws.cell(rr, c_idx).value
                if val:
                    rr2 = rr
                    while rr2 + 1 <= block_end and ws.cell(rr2 + 1, c_idx).value == val:
                        rr2 += 1
                    if rr2 > rr:
                        ws.merge_cells(start_row=rr, start_column=c_idx,
                                       end_row=rr2, end_column=c_idx)
                    rr = rr2 + 1
                else:
                    rr += 1
        row = block_end + 1

    ws.column_dimensions["A"].width = 16
    ws.column_dimensions["B"].width = 6
    for ci in range(3, last_col + 1):
        ws.column_dimensions[get_column_letter(ci)].width = 22

    # Legende
    leg = row + 1
    ws.cell(leg, 1, "Légende :").font = Font(bold=True, size=9)
    for i, (lab, key) in enumerate(
        [("V1", "V1"), ("V2", "V2"), ("V3", "V3"),
         ("Autres", "AUTRES"), ("Dépassement", "OVER")]
    ):
        lc = ws.cell(leg, 2 + i, lab)
        lc.fill = PatternFill("solid", fgColor=_FILL[key])
        lc.alignment = center; lc.border = border

    ws.freeze_panes = "C4"
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
