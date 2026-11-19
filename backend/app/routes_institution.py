from datetime import date
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .db import get_db
from .models import Organization, SubmittedList, SubmittedRow, User, GraduateProfile, DegreeLevel, now
from .schemas import OrgIn, RowIn
from .deps import institution_any, institution_ok, notify, audit
from .services import level_lookup, list_counts, recompute_list_status
from .logic.importer import parse_rows, ImportError_, TEMPLATE_CSV
from .files import read_limited
from .config import settings
from .routes_company import org_out

router = APIRouter(prefix="/api/institution", tags=["institution"])

STATUS_FR = {"pending": "En attente de contrôle", "invalid": "À corriger", "validated": "Validé", "rejected": "Rejeté", "account_created": "Compte créé"}


def row_out(r: SubmittedRow, db: Session | None = None) -> dict:
    activated = bool(r.user and r.user.status == "active")
    return {"id": r.id, "line_no": r.line_no, "full_name": r.full_name, "email": r.email, "phone": r.phone, "degree_title": r.degree_title,
            "level_code": r.level_code, "specialty": r.specialty, "year": r.year, "honors": r.honors, "country": r.country, "status": r.status,
            "message": r.message, "account_status": r.user.status if r.user else None, "activated": activated}


def list_out(l: SubmittedList, rows: bool = False) -> dict:
    d = {"id": l.id, "title": l.title, "academic_year": l.academic_year, "filename": l.filename, "status": l.status, "note": l.note,
         "created_at": l.created_at.isoformat(), "reviewed_at": l.reviewed_at.isoformat() if l.reviewed_at else None,
         "institution": {"id": l.institution.id, "name": l.institution.name}, "counts": list_counts(l)}
    if rows:
        d["rows"] = [row_out(r) for r in l.rows]
    return d


def row_problems(db: Session, email: str, level_code: str, year: int | None, exclude_row: int | None = None) -> list[str]:
    errs = []
    if not db.scalar(select(func.count()).select_from(DegreeLevel).where(DegreeLevel.code == level_code, DegreeLevel.active)):
        errs.append(f"Niveau inconnu « {level_code} »")
    if db.scalar(select(User).where(User.email == email)):
        errs.append("Un compte existe déjà pour cet email")
    q = select(func.count()).select_from(SubmittedRow).where(SubmittedRow.email == email, SubmittedRow.status.in_(["pending", "validated", "account_created"]))
    if exclude_row:
        q = q.where(SubmittedRow.id != exclude_row)
    if db.scalar(q):
        errs.append("Cet email figure déjà dans une autre liste en cours de traitement")
    if year is not None and not 1970 <= year <= date.today().year + 1:
        errs.append("Année d'obtention improbable")
    return errs


@router.get("/me")
def me(o: Organization = Depends(institution_any), db: Session = Depends(get_db)):
    lists = db.scalars(select(SubmittedList).where(SubmittedList.institution_id == o.id)).all()
    year = now().year
    sent = sum(1 for l in lists if l.created_at.year == year for r in l.rows if r.status != "invalid")
    return {"org": org_out(o), "annual_quota": o.annual_quota, "transmitted_this_year": sent, "lists": len(lists)}


@router.put("/org")
def put_org(data: OrgIn, o: Organization = Depends(institution_any), db: Session = Depends(get_db)):
    for k, v in data.model_dump().items():
        setattr(o, k, v)
    if o.status == "rejected":
        o.status, o.status_reason = "pending", ""
    audit(db, o.owner_id, "org_update"); db.commit()
    return org_out(o)


@router.get("/lists/template.csv")
def template():
    return Response(TEMPLATE_CSV, media_type="text/csv; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="modele_liste_agriconnect.csv"'})


@router.get("/lists")
def lists(o: Organization = Depends(institution_any), db: Session = Depends(get_db)):
    rows = db.scalars(select(SubmittedList).where(SubmittedList.institution_id == o.id).order_by(SubmittedList.id.desc())).all()
    return [list_out(l) for l in rows]


@router.post("/lists", status_code=201)
async def upload_list(title: str = Form(..., min_length=2, max_length=200), academic_year: str = Form("", max_length=20),
                      file: UploadFile = File(...), o: Organization = Depends(institution_ok), db: Session = Depends(get_db)):
    data = await read_limited(file, 5)
    try:
        parsed = parse_rows(file.filename or "", data, level_lookup(db), max_rows=settings.max_list_rows)
    except ImportError_ as e:
        raise HTTPException(422, str(e))
    l = SubmittedList(institution_id=o.id, title=title.strip(), academic_year=academic_year.strip(), filename=(file.filename or "")[:255], status="received")
    db.add(l); db.flush()
    for pr in parsed:
        d = pr.data
        errs = list(pr.errors)
        if not errs:
            errs += row_problems(db, d["email"], d["level_code"], d["year"])
        # doublon dans la même liste déjà signalé par l'import ; on empile pour détecter les doublons internes non détectés ci-dessus
        db.add(SubmittedRow(list_id=l.id, line_no=pr.line_no, full_name=d["nom_complet"], email=d["email"], phone=d["telephone"],
                            degree_title=d["diplome"], level_code=d["level_code"], specialty=d["specialite"], year=d["year"], honors=d["mention"],
                            country=d["pays"], status="invalid" if errs else "pending", message="; ".join(errs)))
        db.flush()
    for a in db.scalars(select(User).where(User.role == "admin", User.status == "active")).all():
        notify(db, a.id, f"Nouvelle liste reçue de {o.name} : « {l.title} » ({len(parsed)} ligne(s))")
    audit(db, o.owner_id, "list_submitted", f"{l.title} ({len(parsed)} lignes)")
    db.commit()
    db.refresh(l)
    return list_out(l, rows=True)


def _own_list(db: Session, lid: int, o: Organization) -> SubmittedList:
    l = db.get(SubmittedList, lid)
    if not l or l.institution_id != o.id:
        raise HTTPException(404, "Liste introuvable")
    return l


@router.get("/lists/{lid}")
def get_list(lid: int, o: Organization = Depends(institution_any), db: Session = Depends(get_db)):
    return list_out(_own_list(db, lid, o), rows=True)


def _own_row(db: Session, lid: int, rid: int, o: Organization):
    l = _own_list(db, lid, o)
    r = db.get(SubmittedRow, rid)
    if not r or r.list_id != l.id:
        raise HTTPException(404, "Ligne introuvable")
    return l, r


def _reopen(l: SubmittedList):
    if l.status in ("validated", "partially_validated", "rejected"):
        l.status, l.reviewed_at = "in_review", None


@router.post("/lists/{lid}/rows", status_code=201)
def add_row(lid: int, data: RowIn, o: Organization = Depends(institution_ok), db: Session = Depends(get_db)):
    l = _own_list(db, lid, o)
    errs = row_problems(db, data.email, data.level_code, data.year)
    n = (db.scalar(select(func.max(SubmittedRow.line_no)).where(SubmittedRow.list_id == l.id)) or 1) + 1
    r = SubmittedRow(list_id=l.id, line_no=n, status="invalid" if errs else "pending", message="; ".join(errs), **data.model_dump())
    db.add(r); _reopen(l); db.commit()
    return row_out(r)


@router.put("/lists/{lid}/rows/{rid}")
def fix_row(lid: int, rid: int, data: RowIn, o: Organization = Depends(institution_ok), db: Session = Depends(get_db)):
    """Correction d'une ligne rejetée ou à corriger. Les lignes validées / dotées d'un compte ne sont plus modifiables."""
    l, r = _own_row(db, lid, rid, o)
    if r.status not in ("invalid", "rejected", "pending"):
        raise HTTPException(409, "Cette ligne a déjà été validée : contactez l'administration pour toute correction")
    for k, v in data.model_dump().items():
        setattr(r, k, v)
    errs = row_problems(db, data.email, data.level_code, data.year, exclude_row=r.id)
    r.status, r.message = ("invalid", "; ".join(errs)) if errs else ("pending", "")
    _reopen(l); audit(db, o.owner_id, "list_row_fixed", f"{lid}/{rid}"); db.commit()
    return row_out(r)


@router.delete("/lists/{lid}/rows/{rid}", status_code=204)
def del_row(lid: int, rid: int, o: Organization = Depends(institution_ok), db: Session = Depends(get_db)):
    l, r = _own_row(db, lid, rid, o)
    if r.status in ("validated", "account_created"):
        raise HTTPException(409, "Cette ligne a déjà été validée")
    db.delete(r); db.flush(); db.refresh(l); recompute_list_status(l); db.commit()


@router.get("/candidates")
def candidates(o: Organization = Depends(institution_any), db: Session = Depends(get_db)):
    """Suivi des candidats transmis : statut de traitement et activation du compte (sans données de profil détaillées)."""
    rows = db.scalars(select(SubmittedRow).join(SubmittedList).where(SubmittedList.institution_id == o.id).order_by(SubmittedRow.id.desc())).all()
    return [{**row_out(r), "list_title": r.list.title} for r in rows]


@router.get("/stats")
def stats(o: Organization = Depends(institution_any), db: Session = Depends(get_db)):
    rows = db.scalars(select(SubmittedRow).join(SubmittedList).where(SubmittedList.institution_id == o.id)).all()
    by_status, by_level, by_year = {}, {}, {}
    for r in rows:
        by_status[r.status] = by_status.get(r.status, 0) + 1
        by_level[r.level_code or "?"] = by_level.get(r.level_code or "?", 0) + 1
        by_year[str(r.year or "?")] = by_year.get(str(r.year or "?"), 0) + 1
    activated = sum(1 for r in rows if r.user and r.user.status == "active")
    created = sum(1 for r in rows if r.user_id)
    profiles = db.scalars(select(GraduateProfile).where(GraduateProfile.institution_id == o.id)).all()
    return {"total_transmitted": len(rows), "by_status": by_status, "by_level": by_level, "by_year": by_year,
            "accounts_created": created, "accounts_activated": activated,
            "activation_rate": round(100 * activated / created) if created else None,
            "profiles_available_now": sum(1 for p in profiles if p.availability == "available"),
            "note": "Statistiques agrégées uniquement : aucune donnée de profil individuelle n'est communiquée à l'établissement."}
