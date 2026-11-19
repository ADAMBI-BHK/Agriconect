import json
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session
from .db import get_db
from .models import (User, GraduateProfile, Degree, Experience, Skill, Achievement, DegreeLevel, Specialty, Opportunity, Application,
                     ApplicationEvent, Organization, Evaluation, Recommendation, Collaboration, Report, OfferMatch, now)
from .schemas import (ProfileIn, DegreeIn, ExperienceIn, SkillIn, AchievementIn, ApplyIn, ResponseIn, ReportIn)
from .deps import require_role, graduate_profile, notify, audit
from .services import (candidate_data, offer_criteria, match_weights, reputation_of, degree_out, exp_out, completeness, current_subscription)
from .logic.matching import match, experience_category
from .files import save_cv, cv_path, delete_cv, read_limited, MIME, save_photo, photo_path, delete_photo, PHOTO_MIME
from .routes_company import opp_out, visible_offer_filter

router = APIRouter(prefix="/api/graduate", tags=["graduate"])
pub = APIRouter(prefix="/api", tags=["referentiels"])


def profile_out(db: Session, p: GraduateProfile) -> dict:
    cd = candidate_data(p)
    return {"id": p.id, "full_name": p.user.full_name, "email": p.user.email, "headline": p.headline, "bio": p.bio, "location": p.location,
            "phone": p.phone, "availability": p.availability, "available_from": p.available_from.isoformat() if p.available_from else None,
            "availability_updated_at": p.availability_updated_at.isoformat(), "visible": p.visible, "show_contact": p.show_contact,
            "show_cv": p.show_cv, "matching_opt_in": p.matching_opt_in, "origin": p.origin, "institution": p.institution.name if p.institution else None,
            "has_cv": bool(p.cv_path), "cv_name": p.cv_name, "has_photo": bool(p.photo_path), "photo_name": p.photo_name,
            "photo_url": "/api/graduate/photo" if p.photo_path else None, "completeness": completeness(p),
            "experience": {"years": cd.experience_years, "category": experience_category(cd.experience_years)},
            "reputation": reputation_of(db, p),
            "degrees": [degree_out(d) for d in p.degrees], "experiences": [exp_out(e) for e in p.experiences],
            "skills": [{"id": s.id, "name": s.name, "verified": s.verified} for s in p.skills],
            "achievements": [{"id": a.id, "title": a.title, "description": a.description, "year": a.year} for a in p.achievements]}


# ------------------------------------------------------------------ référentiels publics (formulaires)
@pub.get("/referentials")
def referentials(db: Session = Depends(get_db)):
    lv = db.scalars(select(DegreeLevel).where(DegreeLevel.active).order_by(DegreeLevel.rank, DegreeLevel.id)).all()
    sp = db.scalars(select(Specialty).where(Specialty.active).order_by(Specialty.name)).all()
    return {"levels": [{"id": l.id, "code": l.code, "label": l.label, "family": l.family, "rank": l.rank} for l in lv],
            "specialties": [{"id": s.id, "name": s.name, "domain": s.domain} for s in sp]}


# ------------------------------------------------------------------ profil
@router.get("/profile")
def get_profile(p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    return profile_out(db, p)


@router.put("/profile")
def put_profile(data: ProfileIn, p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    if data.availability != p.availability or data.available_from != p.available_from:
        p.availability_updated_at = now()
    values = data.model_dump()
    if values.get("matching_opt_in") != p.matching_opt_in:
        p.matching_consent_at = now()
        if not values.get("matching_opt_in"):
            db.query(OfferMatch).filter(OfferMatch.graduate_id == p.id).delete(synchronize_session=False)
    for k, v in values.items():
        setattr(p, k, v)
    audit(db, p.user_id, "profile_update"); db.commit()
    return profile_out(db, p)


@router.post("/photo")
async def upload_photo(file: UploadFile = File(...), p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    data = await read_limited(file, max_mb=2)
    stored, name = save_photo(file.filename or "", data)
    delete_photo(p.photo_path)
    p.photo_path, p.photo_name = stored, name
    audit(db, p.user_id, "profile_photo_upload"); db.commit()
    return {"has_photo": True, "photo_name": name, "photo_url": "/api/graduate/photo"}


@router.get("/photo")
def download_photo(p: GraduateProfile = Depends(graduate_profile)):
    if not p.photo_path:
        raise HTTPException(404, "Aucune photo de profil")
    path = photo_path(p.photo_path)
    return FileResponse(path, media_type=PHOTO_MIME.get(path.suffix, "application/octet-stream"), filename=p.photo_name)


@router.delete("/photo", status_code=204)
def remove_photo(p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    delete_photo(p.photo_path)
    p.photo_path = p.photo_name = ""
    audit(db, p.user_id, "profile_photo_remove"); db.commit()


# ------------------------------------------------------------------ diplômes
def _check_degree_refs(db: Session, data: DegreeIn):
    if not db.get(DegreeLevel, data.level_id):
        raise HTTPException(422, "Niveau de diplôme inconnu")
    if data.specialty_id and not db.get(Specialty, data.specialty_id):
        raise HTTPException(422, "Spécialité inconnue")


@router.post("/degrees", status_code=201)
def add_degree(data: DegreeIn, p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    _check_degree_refs(db, data)
    d = Degree(graduate_id=p.id, status="declared", source="self", **data.model_dump())
    db.add(d); db.commit()
    return degree_out(d)


def _own(db: Session, model, oid: int, p: GraduateProfile):
    o = db.get(model, oid)
    if not o or o.graduate_id != p.id:
        raise HTTPException(404, "Élément introuvable")
    return o


@router.put("/degrees/{did}")
def edit_degree(did: int, data: DegreeIn, p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    d = _own(db, Degree, did, p)
    if d.source == "institution" or d.status == "verified":
        raise HTTPException(409, "Un diplôme vérifié ne peut être modifié que par l'administration (contactez-la pour une correction)")
    _check_degree_refs(db, data)
    for k, v in data.model_dump().items():
        setattr(d, k, v)
    d.status = "declared"
    db.commit()
    return degree_out(d)


@router.delete("/degrees/{did}", status_code=204)
def del_degree(did: int, p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    d = _own(db, Degree, did, p)
    if d.source == "institution" or d.status == "verified":
        raise HTTPException(409, "Un diplôme vérifié ne peut pas être supprimé par le candidat")
    db.delete(d); db.commit()


# ------------------------------------------------------------------ expériences, compétences, réalisations
@router.post("/experiences", status_code=201)
def add_exp(data: ExperienceIn, p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    e = Experience(graduate_id=p.id, **data.model_dump()); db.add(e); db.commit()
    return exp_out(e)


@router.put("/experiences/{eid}")
def edit_exp(eid: int, data: ExperienceIn, p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    e = _own(db, Experience, eid, p)
    for k, v in data.model_dump().items():
        setattr(e, k, v)
    e.status = "declared"
    db.commit()
    return exp_out(e)


@router.delete("/experiences/{eid}", status_code=204)
def del_exp(eid: int, p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    db.delete(_own(db, Experience, eid, p)); db.commit()


@router.post("/skills", status_code=201)
def add_skill(data: SkillIn, p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    name = data.name.strip()
    if any(s.name.lower() == name.lower() for s in p.skills):
        raise HTTPException(409, "Compétence déjà ajoutée")
    if len(p.skills) >= 50:
        raise HTTPException(409, "Maximum 50 compétences")
    s = Skill(graduate_id=p.id, name=name); db.add(s); db.commit()
    return {"id": s.id, "name": s.name, "verified": s.verified}


@router.delete("/skills/{sid}", status_code=204)
def del_skill(sid: int, p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    db.delete(_own(db, Skill, sid, p)); db.commit()


@router.post("/achievements", status_code=201)
def add_ach(data: AchievementIn, p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    a = Achievement(graduate_id=p.id, **data.model_dump()); db.add(a); db.commit()
    return {"id": a.id, "title": a.title, "description": a.description, "year": a.year}


@router.delete("/achievements/{aid}", status_code=204)
def del_ach(aid: int, p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    db.delete(_own(db, Achievement, aid, p)); db.commit()


# ------------------------------------------------------------------ CV
@router.post("/cv")
async def upload_cv(file: UploadFile = File(...), p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    data = await read_limited(file)
    stored, name = save_cv(file.filename or "", data)
    delete_cv(p.cv_path)
    p.cv_path, p.cv_name = stored, name
    audit(db, p.user_id, "cv_upload"); db.commit()
    return {"has_cv": True, "cv_name": name}


@router.get("/cv")
def download_cv(p: GraduateProfile = Depends(graduate_profile)):
    if not p.cv_path:
        raise HTTPException(404, "Aucun CV")
    path = cv_path(p.cv_path)
    return FileResponse(path, media_type=MIME.get(path.suffix, "application/octet-stream"), filename=p.cv_name)


@router.delete("/cv", status_code=204)
def remove_cv(p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    delete_cv(p.cv_path); p.cv_path = p.cv_name = ""; db.commit()


# ------------------------------------------------------------------ offres « pour moi » et candidatures
@router.get("/matching")
def my_matching(p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    if not p.matching_opt_in:
        return []
    rows = db.scalars(select(OfferMatch).join(Opportunity, Opportunity.id == OfferMatch.opportunity_id)
                      .where(OfferMatch.graduate_id == p.id, *visible_offer_filter(db))
                      .order_by(OfferMatch.created_at.desc())).all()
    return [{"id": r.id, "offer_id": r.opportunity_id, "title": db.get(Opportunity, r.opportunity_id).title,
             "score": r.score, "rank": r.rank, "total": r.total, "criteria": json.loads(r.criteria_json),
             "created_at": r.created_at.isoformat()} for r in rows]


@router.get("/offers")
def offers_for_me(q: str = "", type: str = "", location: str = "", page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=50),
                  p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    cond = visible_offer_filter(db)
    if q:
        cond.append(or_(Opportunity.title.ilike(f"%{q}%"), Opportunity.description.ilike(f"%{q}%")))
    if type:
        cond.append(Opportunity.type == type)
    if location:
        cond.append(Opportunity.location == location)
    total = db.scalar(select(func.count()).select_from(Opportunity).where(*cond))
    rows = db.scalars(select(Opportunity).where(*cond).order_by(Opportunity.created_at.desc()).offset((page - 1) * size).limit(size)).all()
    cd, w = candidate_data(p), match_weights(db)
    applied = set(db.scalars(select(Application.opportunity_id).where(Application.graduate_id == p.user_id)).all())
    items = []
    for o in rows:
        m = match(offer_criteria(o), cd, w) if p.matching_opt_in else None
        items.append({**opp_out(o), "my_match": ({"score": m["score"], "criteria": m["criteria"], "blocking_missing": m["blocking_missing"],
                                                  "to_verify": m["to_verify"], "note": m["note"]} if m else None), "applied": o.id in applied})
    return {"total": total, "page": page, "size": size, "items": items}


def app_out(a: Application) -> dict:
    o = a.opportunity
    return {"id": a.id, "status": a.status, "cover_letter": a.cover_letter, "created_at": a.created_at.isoformat(),
            "opportunity": {"id": o.id, "title": o.title, "org": o.org.name, "degree_level": o.level.label}}


@router.post("/offers/{oid}/apply", status_code=201)
def apply(oid: int, data: ApplyIn, p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    o = db.scalar(select(Opportunity).where(Opportunity.id == oid, *visible_offer_filter(db)))
    if not o:
        raise HTTPException(404, "Opportunité indisponible")
    if db.scalar(select(Application).where(Application.opportunity_id == oid, Application.graduate_id == p.user_id)):
        raise HTTPException(409, "Vous avez déjà candidaté")
    a = Application(opportunity_id=oid, graduate_id=p.user_id, cover_letter=data.cover_letter)
    db.add(a); db.flush()
    db.add(ApplicationEvent(application_id=a.id, status="submitted", actor_id=p.user_id))
    notify(db, o.org.owner_id, f"Nouvelle candidature de {p.user.full_name} pour « {o.title} »")
    db.commit()
    return app_out(a)


@router.get("/applications")
def my_apps(p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    rows = db.scalars(select(Application).where(Application.graduate_id == p.user_id).order_by(Application.created_at.desc())).all()
    out = []
    for a in rows:
        ev = db.scalars(select(ApplicationEvent).where(ApplicationEvent.application_id == a.id).order_by(ApplicationEvent.id)).all()
        out.append({**app_out(a), "history": [{"status": e.status, "comment": e.comment if e.actor_id != p.user_id else "", "created_at": e.created_at.isoformat()} for e in ev]})
    return out


@router.post("/applications/{aid}/withdraw")
def withdraw(aid: int, p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    a = db.get(Application, aid)
    if not a or a.graduate_id != p.user_id:
        raise HTTPException(404, "Candidature introuvable")
    if a.status in ("accepted", "rejected", "withdrawn"):
        raise HTTPException(409, "Candidature déjà clôturée")
    a.status = "withdrawn"
    db.add(ApplicationEvent(application_id=a.id, status="withdrawn", actor_id=p.user_id))
    notify(db, a.opportunity.org.owner_id, f"{p.user.full_name} a retiré sa candidature pour « {a.opportunity.title} »")
    db.commit()
    return app_out(a)


# ------------------------------------------------------------------ évaluations reçues : information, réponse, contestation
@router.get("/evaluations")
def my_evals(p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    ev = db.scalars(select(Evaluation).where(Evaluation.graduate_id == p.id, Evaluation.status != "hidden").order_by(Evaluation.id.desc())).all()
    recos = db.scalars(select(Recommendation).where(Recommendation.graduate_id == p.id, Recommendation.status == "published")).all()
    return {"evaluations": [{"id": e.id, "company": e.company.name, "status": e.status, "average": round(e.average, 2), "comment": e.comment,
                             "response": e.response, "technical": e.technical, "deadlines": e.deadlines, "adaptability": e.adaptability,
                             "professionalism": e.professionalism, "teamwork": e.teamwork, "results": e.results,
                             "mission": e.collaboration.title, "created_at": e.created_at.isoformat()} for e in ev],
            "recommendations": [{"id": r.id, "company": r.company.name, "text": r.text, "created_at": r.created_at.isoformat()} for r in recos]}


@router.post("/evaluations/{eid}/respond")
def respond(eid: int, data: ResponseIn, p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    e = db.get(Evaluation, eid)
    if not e or e.graduate_id != p.id or e.status == "hidden":
        raise HTTPException(404, "Évaluation introuvable")
    e.response = data.response
    notify(db, e.company.owner_id, f"{p.user.full_name} a répondu à votre évaluation.")
    db.commit()
    return {"ok": True}


@router.post("/evaluations/{eid}/contest")
def contest(eid: int, data: ReportIn, p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    e = db.get(Evaluation, eid)
    if not e or e.graduate_id != p.id or e.status == "hidden":
        raise HTTPException(404, "Évaluation introuvable")
    if data.kind != "evaluation" or data.target_id != eid:
        raise HTTPException(422, "Requête incohérente")
    db.add(Report(kind="evaluation", target_id=eid, reporter_id=p.user_id, reason=data.reason))
    e.status = "contested"  # retirée du calcul de réputation jusqu'à la décision de l'administration
    for a in db.scalars(select(User).where(User.role == "admin", User.status == "active")).all():
        notify(db, a.id, f"Contestation d'une évaluation par {p.user.full_name}")
    db.commit()
    return {"ok": True}


@router.get("/collaborations")
def my_collabs(p: GraduateProfile = Depends(graduate_profile), db: Session = Depends(get_db)):
    rows = db.scalars(select(Collaboration).where(Collaboration.graduate_id == p.id).order_by(Collaboration.id.desc())).all()
    return [{"id": c.id, "company": c.company.name, "title": c.title, "kind": c.kind, "status": c.status,
             "start_date": c.start_date.isoformat(), "end_date": c.end_date.isoformat() if c.end_date else None} for c in rows]
