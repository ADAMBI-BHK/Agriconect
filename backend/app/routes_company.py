from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from .db import get_db
from .models import (User, Organization, Opportunity, Application, ApplicationEvent, GraduateProfile, Degree, DegreeLevel, Specialty,
                     Skill, Subscription, ProfileView, Collaboration, Evaluation, Recommendation, TalentSelection)
from .schemas import OrgIn, OppIn, OppPatch, StatusIn, CollabIn, EvalIn, RecoIn, SelectTalentsIn
from .deps import company_any, company_ok, notify, audit
from .services import (entitlements, require_subscription, active_offers_count, views_used, candidate_data, offer_criteria, match_weights,
                       talent_summary, degree_out, exp_out, reputation_of, current_subscription)
from .logic.matching import match, experience_category
from .logic.entitlements import quota_allows, month_key
from .logic.text import csv_list, norm
from .files import cv_path, MIME

router = APIRouter(prefix="/api/company", tags=["company"])

TRANSITIONS = {"submitted": {"received", "under_review", "rejected"}, "received": {"under_review", "rejected"},
               "under_review": {"shortlisted", "rejected"}, "shortlisted": {"interview", "rejected"}, "interview": {"accepted", "rejected"}}


# ------------------------------------------------------------------ sérialisation des offres (partagée)
def visible_offer_filter(db: Session) -> list:
    """Conditions SQL d'une offre visible des candidats : publiée, non suspendue, non échue, entreprise validée ET abonnement actif."""
    today = date.today()
    subs = select(Subscription.org_id).where(Subscription.status == "active", Subscription.start_date <= today, Subscription.end_date >= today)
    ok_orgs = select(Organization.id).where(Organization.status == "validated", Organization.id.in_(subs))
    return [Opportunity.status == "published", Opportunity.moderation == "ok",
            or_(Opportunity.deadline.is_(None), Opportunity.deadline >= today), Opportunity.org_id.in_(ok_orgs)]


def opp_out(o: Opportunity, detail: bool = True) -> dict:
    d = {"id": o.id, "title": o.title, "description": o.description, "sector": o.sector, "type": o.type, "contract_type": o.contract_type,
         "duration": o.duration, "salary": {"type": o.salary_type, "min": o.salary_min, "max": o.salary_max, "period": o.salary_period, "currency": o.salary_currency}, "benefits": o.benefits, "review_reason": o.review_reason, "reviewed_at": o.reviewed_at.isoformat() if o.reviewed_at else None, "location": o.location, "status": o.status, "moderation": o.moderation,
         "deadline": o.deadline.isoformat() if o.deadline else None, "created_at": o.created_at.isoformat(),
         "org": {"id": o.org.id, "name": o.org.name, "verified": o.org.verified},
         "degree": {"level": {"id": o.level.id, "code": o.level.code, "label": o.level.label}, "mandatory": o.degree_mandatory,
                    "accepted_level_codes": csv_list(o.accepted_level_codes), "accepted_titles": csv_list(o.accepted_titles),
                    "allow_higher": o.allow_higher, "allow_lower_alt": o.allow_lower_alt},
         "specialty": {"id": o.specialty.id, "name": o.specialty.name} if o.specialty else None, "specialty_required": o.specialty_required,
         "experience": {"min_years": o.min_experience_years, "mandatory": o.experience_mandatory},
         "required_skills": csv_list(o.required_skills), "desired_skills": csv_list(o.desired_skills), "requirements": o.requirements}
    return d


# ------------------------------------------------------------------ organisation et tableau de bord
def org_out(o: Organization) -> dict:
    return {"id": o.id, "kind": o.kind, "name": o.name, "description": o.description, "sector": o.sector, "city": o.city, "country": o.country,
            "website": o.website, "phone": o.phone, "registration_no": o.registration_no, "status": o.status, "status_reason": o.status_reason,
            "verified": o.verified}


@router.get("/me")
def me(o: Organization = Depends(company_any), db: Session = Depends(get_db)):
    return {"org": org_out(o), "entitlements": entitlements(db, o)}


@router.put("/org")
def put_org(data: OrgIn, o: Organization = Depends(company_any), db: Session = Depends(get_db)):
    for k, v in data.model_dump().items():
        setattr(o, k, v)
    if o.status == "rejected":  # nouvelle soumission après un rejet
        o.status, o.status_reason = "pending", ""
        for a in db.scalars(select(User).where(User.role == "admin", User.status == "active")).all():
            notify(db, a.id, f"Dossier entreprise mis à jour : {o.name}")
    audit(db, o.owner_id, "org_update"); db.commit()
    return org_out(o)


@router.get("/dashboard")
def dashboard(o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    by = dict(db.execute(select(Opportunity.status, func.count()).where(Opportunity.org_id == o.id).group_by(Opportunity.status)).all())
    apps = db.scalar(select(func.count()).select_from(Application).join(Opportunity).where(Opportunity.org_id == o.id)) or 0
    new = db.scalar(select(func.count()).select_from(Application).join(Opportunity).where(Opportunity.org_id == o.id, Application.status == "submitted")) or 0
    return {"offers_by_status": by, "applications": apps, "applications_new": new, "entitlements": entitlements(db, o)}


# ------------------------------------------------------------------ offres
def _validate_offer_refs(db: Session, level_id, specialty_id, codes):
    if level_id is not None:
        lv = db.get(DegreeLevel, level_id)
        if not lv or not lv.active:
            raise HTTPException(422, "Niveau de diplôme requis invalide : l'entreprise doit en choisir un dans la liste")
    if specialty_id is not None and not db.get(Specialty, specialty_id):
        raise HTTPException(422, "Spécialité inconnue")
    if codes:
        known = set(db.scalars(select(DegreeLevel.code)).all())
        bad = [c for c in codes if c not in known]
        if bad:
            raise HTTPException(422, "Niveaux acceptés inconnus : " + ", ".join(bad))


def _check_publish(db: Session, o: Organization, exclude_id: int | None, deadline: date | None):
    plan = require_subscription(db, o)
    if not quota_allows(plan.max_active_offers, active_offers_count(db, o.id, exclude_id)):
        raise HTTPException(402, f"Quota atteint : votre formule {plan.name} autorise {plan.max_active_offers} offre(s) publiée(s) à la fois. "
                                 "Archivez ou suspendez une offre, ou changez de formule.")
    if deadline and deadline < date.today():
        raise HTTPException(422, "La date limite est dépassée")


def _check_submission(deadline: date | None):
    """La soumission est contrôlée par l'administration ; l'accès est vérifié à l'approbation."""
    if deadline and deadline < date.today():
        raise HTTPException(422, "La date limite est dépassée")


def _owned(db: Session, oid: int, o: Organization) -> Opportunity:
    x = db.get(Opportunity, oid)
    if not x or x.org_id != o.id:
        raise HTTPException(404, "Offre introuvable")
    return x


LIST_FIELDS = ("accepted_level_codes", "accepted_titles", "required_skills", "desired_skills")


def _validate_salary(values: dict):
    kind = values.get("salary_type", "negotiable")
    minimum, maximum = values.get("salary_min"), values.get("salary_max")
    if kind == "fixed" and minimum is None:
        raise HTTPException(422, "Indiquez le montant de la rémunération fixe")
    if kind == "range":
        if minimum is None or maximum is None:
            raise HTTPException(422, "Indiquez les deux bornes de la fourchette salariale")
        if minimum > maximum:
            raise HTTPException(422, "La rémunération minimale ne peut pas dépasser la rémunération maximale")

def _apply(o: Opportunity, values: dict):
    for k, v in values.items():
        setattr(o, k, ",".join(x.strip() for x in v if x.strip()) if k in LIST_FIELDS and v is not None else v)


@router.get("/offers")
def my_offers(o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    rows = db.scalars(select(Opportunity).where(Opportunity.org_id == o.id).order_by(Opportunity.created_at.desc())).all()
    counts = dict(db.execute(select(Opportunity.id, func.count(Application.id)).select_from(Opportunity)
                             .join(Application, Application.opportunity_id == Opportunity.id, isouter=True).where(Opportunity.org_id == o.id).group_by(Opportunity.id)).all())
    return [{**opp_out(x), "applications": counts.get(x.id, 0)} for x in rows]


@router.post("/offers", status_code=201)
def create_offer(data: OppIn, o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    _validate_offer_refs(db, data.degree_level_id, data.specialty_id, data.accepted_level_codes)
    values = data.model_dump()
    _validate_salary(values)
    # Toute nouvelle offre démarre en brouillon : seule l’administration peut la publier.
    values["status"] = "draft"
    x = Opportunity(org_id=o.id, **{k: ("" if k in LIST_FIELDS else v) for k, v in values.items()})
    _apply(x, values)
    db.add(x); audit(db, o.owner_id, "offer_create", data.title); db.commit()
    return opp_out(x)


@router.get("/offers/{oid}")
def get_offer(oid: int, o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    return opp_out(_owned(db, oid, o))


@router.patch("/offers/{oid}")
def patch_offer(oid: int, data: OppPatch, o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    x = _owned(db, oid, o)
    vals = data.model_dump(exclude_unset=True)
    if "degree_level_id" in vals and vals["degree_level_id"] is None:
        raise HTTPException(422, "Le niveau de diplôme requis ne peut pas être vide")
    _validate_offer_refs(db, vals.get("degree_level_id"), vals.get("specialty_id"), vals.get("accepted_level_codes"))
    salary_values = {"salary_type": vals.get("salary_type", x.salary_type), "salary_min": vals.get("salary_min", x.salary_min), "salary_max": vals.get("salary_max", x.salary_max)}
    _validate_salary(salary_values)
    requested_status = vals.pop("status", None)
    if requested_status == "pending_review":
        if x.status not in ("draft", "changes_requested", "paused", "published"):
            raise HTTPException(409, "Cette offre ne peut pas être soumise dans son état actuel")
        if x.moderation == "suspended":
            raise HTTPException(403, "Cette offre est suspendue par l'administration")
        _check_submission(vals.get("deadline", x.deadline))
        x.status, x.review_reason, x.reviewed_at = "pending_review", "", None
    elif requested_status == "published":
        raise HTTPException(403, "La publication doit être approuvée par l'administration AgriConnect")
    elif requested_status in ("paused", "archived"):
        if x.status != "published" and requested_status == "paused":
            raise HTTPException(409, "Seule une offre publiée peut être suspendue")
        x.status = requested_status
    if x.status == "published" and vals:
        x.status, x.review_reason, x.reviewed_at = "pending_review", "Modification soumise à une nouvelle vérification.", None
    _apply(x, {k: v for k, v in vals.items() if v is not None or k in ("deadline", "specialty_id", "salary_min", "salary_max")})
    audit(db, o.owner_id, "offer_update", str(oid)); db.commit()
    return opp_out(x)


@router.delete("/offers/{oid}", status_code=204)
def delete_offer(oid: int, o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    x = _owned(db, oid, o)
    if db.scalar(select(func.count()).select_from(Application).where(Application.opportunity_id == oid)):
        raise HTTPException(409, "Des candidatures existent : archivez l'offre au lieu de la supprimer")
    db.delete(x); audit(db, o.owner_id, "offer_delete", str(oid)); db.commit()


# ------------------------------------------------------------------ candidatures reçues
def _applicant_view(db: Session, a: Application, offer: Opportunity, ent: dict, weights: dict, org_id: int) -> dict:
    p = db.scalar(select(GraduateProfile).where(GraduateProfile.user_id == a.graduate_id))
    d = {"id": a.id, "status": a.status, "cover_letter": a.cover_letter, "created_at": a.created_at.isoformat(),
         "graduate": {"id": p.id, "full_name": a.graduate.full_name, "email": a.graduate.email, "has_cv": bool(p.cv_path)}}
    d["profile"] = talent_summary(db, p)
    d["degrees"] = [degree_out(x) for x in p.degrees]  # intitulé exact + statut de vérification toujours affichés
    if ent["can_see_matching"] and p.matching_opt_in:
        m = match(offer_criteria(offer), candidate_data(p), weights)
        d["match"] = m
    else:
        d["match"] = None
        d["match_locked"] = ("Le talent n'a pas activé le matching ; vous pouvez examiner sa candidature manuellement." if not p.matching_opt_in
                             else "La correspondance expliquée est réservée aux formules Professional et Business.")
    recos = db.scalars(select(Recommendation).where(Recommendation.graduate_id == p.id, Recommendation.status == "published",
                                                     Recommendation.company_id != org_id)).all()
    d["recommendations"] = [{"id": r.id, "company": r.company.name, "text": r.text, "created_at": r.created_at.isoformat()} for r in recos]
    return d


@router.get("/offers/{oid}/applications")
def offer_applications(oid: int, o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    offer = _owned(db, oid, o)
    ent, w = entitlements(db, o), match_weights(db)
    rows = db.scalars(select(Application).where(Application.opportunity_id == oid).order_by(Application.created_at)).all()
    return [_applicant_view(db, a, offer, ent, w, o.id) for a in rows]


def _app_of(db: Session, aid: int, o: Organization) -> Application:
    a = db.get(Application, aid)
    if not a or a.opportunity.org_id != o.id:
        raise HTTPException(404, "Candidature introuvable")
    return a


@router.patch("/applications/{aid}/status")
def set_status(aid: int, data: StatusIn, o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    a = _app_of(db, aid, o)
    if data.status not in TRANSITIONS.get(a.status, set()):
        raise HTTPException(409, f"Transition interdite : {a.status} → {data.status}")
    a.status = data.status
    db.add(ApplicationEvent(application_id=a.id, status=data.status, actor_id=o.owner_id, comment=data.comment))
    notify(db, a.graduate_id, f"Votre candidature « {a.opportunity.title} » est passée au statut : {data.status}")
    if data.status == "accepted":  # embauche via la plateforme → collaboration vérifiée (permet ensuite l'évaluation)
        p = db.scalar(select(GraduateProfile).where(GraduateProfile.user_id == a.graduate_id))
        kind = a.opportunity.type if a.opportunity.type in ("job", "internship", "apprenticeship", "mission") else "mission"
        if not db.scalar(select(Collaboration).where(Collaboration.company_id == o.id, Collaboration.graduate_id == p.id, Collaboration.title == a.opportunity.title)):
            db.add(Collaboration(company_id=o.id, graduate_id=p.id, kind=kind, title=a.opportunity.title, start_date=date.today(),
                                 source="platform", status="verified"))
    db.commit()
    return {"id": a.id, "status": a.status}


@router.get("/applications/{aid}/cv")
def applicant_cv(aid: int, o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    a = _app_of(db, aid, o)
    p = db.scalar(select(GraduateProfile).where(GraduateProfile.user_id == a.graduate_id))
    if not p.cv_path:
        raise HTTPException(404, "Aucun CV")
    path = cv_path(p.cv_path)
    return FileResponse(path, media_type=MIME.get(path.suffix, "application/octet-stream"), filename=p.cv_name)


# ------------------------------------------------------------------ recherche de talents (soumise à l'abonnement)
ADVANCED = ("specialty_id", "skills", "min_years", "max_years", "availability", "institution_id")


def _searchable(db: Session):
    return [User.status == "active", GraduateProfile.visible.is_(True)]


def _match_sort_key(item):
    """Priorise d'abord le niveau d'étude requis, puis les autres critères du score."""
    _, result = item
    degree = next((c for c in result["criteria"] if c["key"] == "degree"), None)
    degree_missing = not degree or degree["ratio"] <= 0
    return (degree_missing, bool(result["blocking_missing"]), -result["score"])


@router.get("/talents")
def search_talents(q: str = "", level_id: int | None = None, location: str = "", specialty_id: int | None = None, skills: str = "",
                   min_years: float | None = None, max_years: float | None = None, availability: str = "", institution_id: int | None = None,
                   offer_id: int | None = None, page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=30),
                   o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    plan = require_subscription(db, o)
    if not plan.can_search:
        raise HTTPException(403, f"La recherche de talents n'est pas incluse dans la formule {plan.name}.")
    used_adv = [k for k, v in dict(specialty_id=specialty_id, skills=skills, min_years=min_years, max_years=max_years,
                                   availability=availability, institution_id=institution_id).items() if v not in (None, "")]
    if used_adv and not plan.can_advanced_filters:
        raise HTTPException(403, f"Les filtres avancés ({', '.join(used_adv)}) ne sont pas inclus dans la formule {plan.name}.")
    offer = None
    if offer_id:
        if not plan.can_see_matching:
            raise HTTPException(403, f"La correspondance avec une offre n'est pas incluse dans la formule {plan.name}.")
        offer = _owned(db, offer_id, o)
    cond = [GraduateProfile.user_id == User.id, *_searchable(db)]
    if offer:
        # Le classement algorithmique n'inclut que les talents ayant activé leur consentement.
        cond.append(GraduateProfile.matching_opt_in.is_(True))
    if location:
        cond.append(GraduateProfile.location == location)
    if availability:
        cond.append(GraduateProfile.availability == availability)
    if institution_id:
        cond.append(GraduateProfile.institution_id == institution_id)
    if q:
        like = f"%{q}%"
        cond.append(or_(GraduateProfile.headline.ilike(like), GraduateProfile.bio.ilike(like),
                        GraduateProfile.id.in_(select(Skill.graduate_id).where(Skill.name.ilike(like))),
                        GraduateProfile.id.in_(select(Degree.graduate_id).where(Degree.title.ilike(like)))))
    if level_id:  # niveau de diplôme : au moins ce niveau (filtre distinct de l'expérience)
        rk = db.scalar(select(DegreeLevel.rank).where(DegreeLevel.id == level_id))
        if rk is None:
            raise HTTPException(422, "Niveau inconnu")
        cond.append(GraduateProfile.id.in_(select(Degree.graduate_id).join(DegreeLevel).where(DegreeLevel.rank >= rk, Degree.status != "rejected")))
    if specialty_id:
        cond.append(GraduateProfile.id.in_(select(Degree.graduate_id).where(Degree.specialty_id == specialty_id, Degree.status != "rejected")))
    profiles = db.scalars(select(GraduateProfile).join(User, GraduateProfile.user_id == User.id).where(*cond).limit(600)).all()
    want = [norm(s) for s in csv_list(skills)]
    w = match_weights(db)
    items = []
    for p in profiles:
        cd = candidate_data(p)
        if want and not all(s in cd.skills for s in want):
            continue
        if min_years is not None and cd.experience_years < min_years:
            continue
        if max_years is not None and cd.experience_years > max_years:
            continue
        m = None
        if offer:
            m = match(offer_criteria(offer), cd, w)
        items.append((p, m))
    if offer:  # classement contextualisé : niveau requis d'abord, puis adéquation à l'offre
        items.sort(key=_match_sort_key)
    else:
        items.sort(key=lambda x: -reputation_of(db, x[0])["score"])
    total = len(items)
    page_items = items[(page - 1) * size: page * size]
    return {"total": total, "page": page, "size": size,
            "items": [talent_summary(db, p, m) for p, m in page_items],
            "note": "Les noms et coordonnées ne sont affichés qu'à l'ouverture d'un profil (consultation comptée dans votre quota mensuel)."}


def _profile_detail(db: Session, p: GraduateProfile, ent: dict) -> dict:
    rep = reputation_of(db, p)
    d = talent_summary(db, p)
    d.update({"full_name": p.user.full_name, "bio": p.bio, "degrees": [degree_out(x) for x in p.degrees],
              "experiences": [exp_out(e) for e in p.experiences],
              "skills": [{"name": s.name, "verified": s.verified} for s in p.skills],
              "achievements": [{"title": a.title, "description": a.description, "year": a.year} for a in p.achievements],
              "reputation": rep, "availability_note": "Disponibilité mise à jour le " + p.availability_updated_at.date().isoformat()})
    if ent["can_see_contacts"] and p.show_contact:
        d["contact"] = {"email": p.user.email, "phone": p.phone}
    else:
        d["contact"] = None
        d["contact_note"] = ("Coordonnées non visibles : " + ("le talent ne les a pas autorisées." if ent["can_see_contacts"]
                                                                else "réservées à la formule Business."))
    d["can_download_cv"] = bool(p.cv_path and p.show_cv and ent["can_see_contacts"])
    return d


@router.get("/talents/{pid}")
def talent_detail(pid: int, offer_id: int | None = None, o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    plan = require_subscription(db, o)
    if not plan.can_search:
        raise HTTPException(403, f"La consultation des profils n'est pas incluse dans la formule {plan.name}.")
    p = db.get(GraduateProfile, pid)
    if not p or not p.visible or p.user.status != "active":
        raise HTTPException(404, "Profil introuvable ou non visible")
    month = month_key()
    seen = db.scalar(select(ProfileView).where(ProfileView.company_id == o.id, ProfileView.graduate_id == pid, ProfileView.month == month))
    if not seen:
        if not quota_allows(plan.profile_views_per_month, views_used(db, o.id)):
            raise HTTPException(402, f"Quota mensuel atteint : {plan.profile_views_per_month} profil(s) consultable(s) avec la formule {plan.name}.")
        db.add(ProfileView(company_id=o.id, graduate_id=pid, month=month)); db.commit()
    ent = entitlements(db, o)
    out = _profile_detail(db, p, ent)
    if offer_id and plan.can_see_matching and p.matching_opt_in:
        out["match"] = match(offer_criteria(_owned(db, offer_id, o)), candidate_data(p), match_weights(db))
    elif offer_id and not p.matching_opt_in:
        out["match_note"] = "Ce talent n'a pas activé le matching ; son profil reste consultable selon ses paramètres de visibilité."
    out["quota"] = ent["views"]
    return out


@router.get("/talents/{pid}/cv")
def talent_cv(pid: int, o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    plan = require_subscription(db, o)
    p = db.get(GraduateProfile, pid)
    seen = db.scalar(select(ProfileView).where(ProfileView.company_id == o.id, ProfileView.graduate_id == pid, ProfileView.month == month_key()))
    if not p or not p.visible or not plan.can_see_contacts or not p.show_cv or not p.cv_path or not seen:
        raise HTTPException(403, "CV non accessible (formule, autorisation du talent ou consultation préalable manquante)")
    path = cv_path(p.cv_path)
    return FileResponse(path, media_type=MIME.get(path.suffix, "application/octet-stream"), filename=p.cv_name)


@router.get("/offers/{oid}/recommendations")
def recommendations(oid: int, limit: int = Query(20, ge=1, le=50), o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    """Talents recommandés pour une offre, avec explication critère par critère."""
    plan = require_subscription(db, o)
    if not (plan.can_search and plan.can_see_matching):
        raise HTTPException(403, f"Les recommandations ne sont pas incluses dans la formule {plan.name}.")
    offer = _owned(db, oid, o)
    crit, w = offer_criteria(offer), match_weights(db)
    profiles = db.scalars(select(GraduateProfile).join(User, GraduateProfile.user_id == User.id).where(
        *_searchable(db), GraduateProfile.matching_opt_in.is_(True)).limit(600)).all()
    res = [(p, match(crit, candidate_data(p), w)) for p in profiles]
    res.sort(key=_match_sort_key)
    return {"offer": {"id": offer.id, "title": offer.title}, "items": [talent_summary(db, p, m) for p, m in res[:limit]],
            "note": "Les profils ayant le niveau requis apparaissent en premier, puis le score départage les profils. Aucun profil n'est exclu automatiquement."}


@router.post("/selections", status_code=201)
def select_talents(data: SelectTalentsIn, o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    """Enregistre une sélection liée à une offre et notifie chaque talent une seule fois."""
    plan = require_subscription(db, o)
    if not (plan.can_search and plan.can_see_matching):
        raise HTTPException(403, f"La sélection de talents n'est pas incluse dans la formule {plan.name}.")
    offer = _owned(db, data.offer_id, o)
    requested = list(dict.fromkeys(data.graduate_ids))
    profiles = db.scalars(select(GraduateProfile).join(User, GraduateProfile.user_id == User.id).where(
        GraduateProfile.id.in_(requested), *_searchable(db), GraduateProfile.matching_opt_in.is_(True))).all()
    by_id = {p.id: p for p in profiles}
    selected, already, unavailable = [], [], []
    for pid in requested:
        p = by_id.get(pid)
        if not p:
            unavailable.append(pid)
            continue
        existing = db.scalar(select(TalentSelection).where(TalentSelection.company_id == o.id,
                                                            TalentSelection.opportunity_id == offer.id,
                                                            TalentSelection.graduate_id == pid))
        if existing:
            already.append(pid)
            continue
        db.add(TalentSelection(company_id=o.id, opportunity_id=offer.id, graduate_id=pid))
        notify(db, p.user_id, f"{o.name} vous a sélectionné(e) pour l'offre « {offer.title} ». Consultez votre espace pour en savoir plus.")
        selected.append(pid)
    if not selected and unavailable:
        raise HTTPException(404, "Aucun des profils choisis n'est disponible pour cette sélection")
    audit(db, o.owner_id, "talents_selected", f"offre={offer.id};profils={','.join(map(str, selected))}")
    db.commit()
    return {"selected": selected, "already_selected": already, "unavailable": unavailable}


# ------------------------------------------------------------------ collaborations, évaluations, recommandations
def _known_graduate(db: Session, org_id: int, pid: int) -> bool:
    """Une entreprise ne peut déclarer une collaboration qu'avec un talent qu'elle a consulté ou qui a candidaté chez elle."""
    seen = db.scalar(select(func.count()).select_from(ProfileView).where(ProfileView.company_id == org_id, ProfileView.graduate_id == pid))
    p = db.get(GraduateProfile, pid)
    applied = p and db.scalar(select(func.count()).select_from(Application).join(Opportunity).where(Opportunity.org_id == org_id, Application.graduate_id == p.user_id))
    return bool(seen or applied)


def _collab_out(db: Session, c: Collaboration) -> dict:
    ev = db.scalar(select(Evaluation).where(Evaluation.collaboration_id == c.id))
    rc = db.scalar(select(Recommendation).where(Recommendation.collaboration_id == c.id))
    return {"id": c.id, "graduate": {"id": c.graduate.id, "full_name": c.graduate.user.full_name}, "kind": c.kind, "title": c.title, "source": c.source,
            "status": c.status, "start_date": c.start_date.isoformat(), "end_date": c.end_date.isoformat() if c.end_date else None,
            "evaluated": bool(ev), "evaluation_status": ev.status if ev else None, "evaluation_response": ev.response if ev else "", "recommended": bool(rc)}


@router.get("/collaborations")
def list_collabs(o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    rows = db.scalars(select(Collaboration).where(Collaboration.company_id == o.id).order_by(Collaboration.id.desc())).all()
    return [_collab_out(db, c) for c in rows]


@router.post("/collaborations", status_code=201)
def declare_collab(data: CollabIn, o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    if not _known_graduate(db, o.id, data.graduate_id):
        raise HTTPException(403, "Vous ne pouvez déclarer une collaboration qu'avec un talent dont vous avez consulté le profil ou qui a candidaté chez vous")
    c = Collaboration(company_id=o.id, graduate_id=data.graduate_id, kind=data.kind, title=data.title, start_date=data.start_date,
                      end_date=data.end_date, source="declared", status="pending")
    db.add(c); db.flush()
    for a in db.scalars(select(User).where(User.role == "admin", User.status == "active")).all():
        notify(db, a.id, f"Collaboration à vérifier : {o.name} ↔ talent #{data.graduate_id}")
    audit(db, o.owner_id, "collab_declared", str(c.id)); db.commit()
    return _collab_out(db, c)


def _verified_collab(db: Session, cid: int, o: Organization) -> Collaboration:
    c = db.get(Collaboration, cid)
    if not c or c.company_id != o.id:
        raise HTTPException(404, "Collaboration introuvable")
    if c.status != "verified":
        raise HTTPException(409, "Seule une collaboration vérifiée par l'administration peut donner lieu à une évaluation ou une recommandation")
    return c


@router.post("/evaluations", status_code=201)
def evaluate(data: EvalIn, o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    c = _verified_collab(db, data.collaboration_id, o)
    if db.scalar(select(Evaluation).where(Evaluation.collaboration_id == c.id)):
        raise HTTPException(409, "Cette collaboration a déjà été évaluée")
    e = Evaluation(collaboration_id=c.id, company_id=o.id, graduate_id=c.graduate_id, technical=data.technical, deadlines=data.deadlines,
                   adaptability=data.adaptability, professionalism=data.professionalism, teamwork=data.teamwork, results=data.results,
                   comment=data.comment)
    db.add(e)
    notify(db, c.graduate.user_id, f"{o.name} a publié une évaluation de votre collaboration « {c.title} ». Vous pouvez y répondre ou la contester.")
    audit(db, o.owner_id, "evaluation_created", str(c.id)); db.commit()
    return {"id": e.id, "average": round(e.average, 2)}


@router.post("/recommendations", status_code=201)
def recommend(data: RecoIn, o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    c = _verified_collab(db, data.collaboration_id, o)
    if db.scalar(select(Recommendation).where(Recommendation.collaboration_id == c.id)):
        raise HTTPException(409, "Cette collaboration a déjà fait l'objet d'une recommandation")
    r = Recommendation(collaboration_id=c.id, company_id=o.id, graduate_id=c.graduate_id, text=data.text)
    db.add(r)
    notify(db, c.graduate.user_id, f"{o.name} vous a recommandé(e).")
    audit(db, o.owner_id, "recommendation_created", str(c.id)); db.commit()
    return {"id": r.id}
