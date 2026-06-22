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
    "V1": "8E7CC3",      # violet
    "V2": "6FA8DC",      # bleu
    "V3": "EAD1DC",      # rose clair
    "AUTRES": "ECECEC",  # gris tres clair (quasi blanc)
    "OVER": "FF0000",    # rouge vif (depassement)
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
    thick = Side(style="medium", color=_NAVY)  # separateur entre agents
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left = Alignment(horizontal="left", vertical="top", wrap_text=True)
    head_fill = PatternFill("solid", fgColor=_NAVY)
    head_font = Font(color="FFFFFF", bold=True, size=10)
    agent_fill = PatternFill("solid", fgColor="F1F4F7")
    out_fill = PatternFill("solid", fgColor="F7F8FA")  # jour hors mois

    GAP = 1  # colonne vide etroite entre deux semaines
    n_weeks = len(blocks)

    def _wcol(k):  # colonne du 1er jour de la semaine k (0-indexee)
        return 3 + k * (5 + GAP)

    day_cols = [c for k in range(n_weeks) for c in range(_wcol(k), _wcol(k) + 5)]
    last_col = (_wcol(n_weeks - 1) + 4) if n_weeks else 2
    espace = f" — Espace {space.name}" if space else " — Tous"
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=last_col)
    t = ws.cell(1, 1, f"Suivi du temps — {_MONTHS[month]} {year}{espace}")
    t.font = Font(bold=True, size=13, color=_NAVY)

    ROW_WEEK, ROW_DAY = 2, 3
    for col, label in ((1, "Agent"), (2, "Heure")):
        c = ws.cell(ROW_DAY, col, label)
        c.font = head_font; c.fill = head_fill; c.alignment = center; c.border = border
    for wi, (_iw, days) in enumerate(blocks, start=1):
        cstart = _wcol(wi - 1)
        ws.merge_cells(start_row=ROW_WEEK, start_column=cstart, end_row=ROW_WEEK,
                       end_column=cstart + 4)
        wc = ws.cell(ROW_WEEK, cstart, f"Semaine {wi}")
        wc.font = head_font; wc.fill = head_fill; wc.alignment = center
        for i, (dd, in_month) in enumerate(days):
            hc = ws.cell(ROW_DAY, cstart + i,
                         f"{_DAYS[i]} {dd.day:02d}" if in_month else "")
            hc.font = head_font; hc.fill = head_fill; hc.alignment = center
            hc.border = border

    row = ROW_DAY + 1
    last_block_end = ROW_DAY
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
            for k, (_iw, days) in enumerate(blocks):
                cstart = _wcol(k)
                for i, (dd, in_month) in enumerate(days):
                    cc = ws.cell(r, cstart + i)
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

        # Fusion verticale des heures consecutives identiques (par colonne jour).
        for c_idx in day_cols:
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

        # Ligne EPAISSE au-dessus du bloc -> separation nette entre agents.
        top_sep = Border(top=thick, bottom=thin, left=thin, right=thin)
        for c_idx in (1, 2, *day_cols):
            ws.cell(block_start, c_idx).border = top_sep
        last_block_end = block_end
        row = block_end + 1

    # Ligne epaisse de fermeture sous le dernier agent.
    if employees:
        for c_idx in (1, 2, *day_cols):
            cur = ws.cell(last_block_end, c_idx)
            keep_top = cur.border.top if cur.border else thin
            cur.border = Border(bottom=thick, top=keep_top, left=thin, right=thin)

    ws.column_dimensions["A"].width = 16
    ws.column_dimensions["B"].width = 6
    day_set = set(day_cols)
    for ci in range(3, last_col + 1):
        ws.column_dimensions[get_column_letter(ci)].width = (
            22 if ci in day_set else 2.5)  # gap = colonne etroite

    # Legende (verticale) : libelle (col A) + pastille couleur (col B), par ligne.
    leg = row + 1
    ws.merge_cells(start_row=leg, start_column=1, end_row=leg, end_column=2)
    lt = ws.cell(leg, 1, "Légende")
    lt.font = Font(bold=True, size=9, color=_NAVY)
    lt.alignment = center
    for i, (lab, key) in enumerate(
        [("V1", "V1"), ("V2", "V2"), ("V3", "V3"),
         ("Autres", "AUTRES"), ("Dépassement timer", "OVER")]
    ):
        r = leg + 1 + i
        lc = ws.cell(r, 1, lab)
        lc.font = Font(size=9); lc.border = border; lc.alignment = center
        sw = ws.cell(r, 2)
        sw.fill = PatternFill("solid", fgColor=_FILL[key]); sw.border = border

    ws.freeze_panes = "C4"
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
