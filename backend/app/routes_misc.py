from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from .db import get_db
from .models import (User, Organization, Opportunity, Notification, ContactMessage, Report, Evaluation, Recommendation, GraduateProfile)
from .schemas import ContactIn, ReportIn
from .deps import current_user, notify
from .communes import DEPARTMENTS
from .routes_company import opp_out, visible_offer_filter

router = APIRouter(prefix="/api", tags=["misc"])


@router.get("/geo")
def geo():
    return {"countries": ["Bénin"], "departments": [{"name": d, "communes": c} for d, c in DEPARTMENTS.items()]}


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    c = lambda m, *w: db.scalar(select(func.count()).select_from(m).where(*w))
    return {"graduates": c(User, User.role == "graduate", User.status == "active"),
            "organizations": c(Organization, Organization.kind == "company", Organization.status == "validated"),
            "institutions": c(Organization, Organization.kind == "institution", Organization.status == "validated"),
            "opportunities": c(Opportunity, *visible_offer_filter(db))}


@router.post("/contact", status_code=201)
def contact(data: ContactIn, db: Session = Depends(get_db)):
    db.add(ContactMessage(**data.model_dump())); db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ offres publiques (lecture seule, visibles sans compte)
@router.get("/opportunities")
def list_opps(q: str = "", type: str = "", location: str = "", level_id: int | None = None, page: int = Query(1, ge=1),
              size: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    cond = visible_offer_filter(db)
    if q:
        cond.append(or_(Opportunity.title.ilike(f"%{q}%"), Opportunity.description.ilike(f"%{q}%")))
    if type:
        cond.append(Opportunity.type == type)
    if location:
        cond.append(Opportunity.location == location)
    if level_id:
        cond.append(Opportunity.degree_level_id == level_id)
    total = db.scalar(select(func.count()).select_from(Opportunity).where(*cond))
    rows = db.scalars(select(Opportunity).where(*cond).order_by(Opportunity.created_at.desc()).offset((page - 1) * size).limit(size)).all()
    return {"total": total, "page": page, "size": size, "items": [opp_out(o) for o in rows]}


@router.get("/opportunities/{oid}")
def get_opp(oid: int, db: Session = Depends(get_db)):
    o = db.scalar(select(Opportunity).where(Opportunity.id == oid, *visible_offer_filter(db)))
    if not o:
        raise HTTPException(404, "Opportunité introuvable")
    return opp_out(o)


# ------------------------------------------------------------------ notifications
@router.get("/notifications")
def notifications(u: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Notification).where(Notification.user_id == u.id).order_by(Notification.id.desc()).limit(100)).all()
    return [{"id": n.id, "message": n.message, "read": n.read, "created_at": n.created_at.isoformat()} for n in rows]


@router.get("/notifications/unread-count")
def unread(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"count": db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == u.id, Notification.read.is_(False)))}


@router.post("/notifications/{nid}/read")
def read_notif(nid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    n = db.get(Notification, nid)
    if not n or n.user_id != u.id:
        raise HTTPException(404, "Notification introuvable")
    n.read = True; db.commit()
    return {"ok": True}


@router.post("/notifications/read-all")
def read_all(u: User = Depends(current_user), db: Session = Depends(get_db)):
    for n in db.scalars(select(Notification).where(Notification.user_id == u.id, Notification.read.is_(False))).all():
        n.read = True
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ signalements
@router.post("/reports", status_code=201)
def report(data: ReportIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Signaler une offre, un profil, une évaluation ou une recommandation. Les évaluations et recommandations ne peuvent être
    signalées que par les parties concernées (entreprise auteur ou talent évalué) ; les talents contestent via leur espace."""
    k, t = data.kind, data.target_id
    if k == "offer":
        ok = db.get(Opportunity, t) is not None and u.role in ("graduate", "company", "institution")
    elif k == "profile":
        ok = db.get(GraduateProfile, t) is not None and u.role == "company"
    elif k in ("evaluation", "recommendation"):
        x = db.get(Evaluation if k == "evaluation" else Recommendation, t)
        gp = db.scalar(select(GraduateProfile).where(GraduateProfile.user_id == u.id))
        org = db.scalar(select(Organization).where(Organization.owner_id == u.id))
        ok = bool(x and ((gp and x.graduate_id == gp.id) or (org and x.company_id == org.id)))
    else:
        ok = False
    if not ok:
        raise HTTPException(404, "Élément introuvable ou signalement non autorisé")
    if db.scalar(select(func.count()).select_from(Report).where(Report.kind == k, Report.target_id == t, Report.reporter_id == u.id, Report.status == "open")):
        raise HTTPException(409, "Vous avez déjà signalé cet élément")
    db.add(Report(kind=k, target_id=t, reporter_id=u.id, reason=data.reason))
    for a in db.scalars(select(User).where(User.role == "admin", User.status == "active")).all():
        notify(db, a.id, f"Nouveau signalement ({k} #{t})")
    db.commit()
    return {"ok": True}
