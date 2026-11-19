"""Données de référence (toujours) et données de DÉMONSTRATION (facultatives, clairement fictives)."""
import json
from datetime import date, timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .config import settings
from .models import (User, Organization, DegreeLevel, Specialty, Plan, GraduateProfile, Degree, Experience, Skill, Achievement,
                     Opportunity, OfferMatch, Subscription, Invoice, Payment, SubmittedList, SubmittedRow, Collaboration, Evaluation,
                     Recommendation, Application, ApplicationEvent, now)
from .security import hash_password
from .services import (set_setting, get_setting, create_graduate_account, level_id_by_code, candidate_data, offer_criteria,
                       match_weights)
from .logic.matching import match

LEVELS = [  # code, libellé, famille, rang
    ("TECH", "Technique et professionnel (CAP, BEAT, DEAT)", "Formation technique et professionnelle", 1),
    ("BTS_DUT", "BTS / DUT / DEUST", "Formation supérieure courte", 2),
    ("LIC_PRO", "Licence professionnelle", "Niveau Licence", 3),
    ("LIC_ACAD", "Licence académique (fondamentale, bachelor)", "Niveau Licence", 3),
    ("MASTER", "Master", "Niveau Master", 4),
    ("INGENIEUR", "Diplôme d'ingénieur", "Niveau ingénieur", 4),
    ("DOCTORAT", "Doctorat / PhD", "Niveau Doctorat", 5),
]
SPECIALTIES = [  # nom, domaine
    ("Production végétale", "Agriculture"), ("Horticulture et maraîchage", "Agriculture"), ("Agronomie générale", "Agriculture"),
    ("Protection des végétaux", "Agriculture"), ("Production animale", "Élevage"), ("Santé animale", "Élevage"),
    ("Pêche et aquaculture", "Pêche"), ("Transformation agroalimentaire", "Agroalimentaire"),
    ("Qualité et sécurité alimentaire", "Agroalimentaire"), ("Agroéconomie", "Économie et développement"),
    ("Développement rural", "Économie et développement"), ("Génie rural et machinisme agricole", "Agriculture"),
    ("Gestion des ressources naturelles", "Environnement"),
]
PLANS = [
    dict(code="business", name="Accès entreprise — première année", description="Accès annuel complet au recrutement, au matching et à la sélection des talents.", price_xof=15000,
         duration_days=365, max_active_offers=None, profile_views_per_month=None, can_search=True, can_advanced_filters=True,
         can_see_matching=True, can_see_contacts=True, sort=1),
]
DEMO_PASSWORD = "Demo2026!"
DEMO_DOMAIN = "agriconnect.test"


def seed_reference(db: Session):
    if not db.scalar(select(func.count()).select_from(DegreeLevel)):
        db.add_all(DegreeLevel(code=c, label=l, family=f, rank=r) for c, l, f, r in LEVELS)
    if not db.scalar(select(func.count()).select_from(Specialty)):
        db.add_all(Specialty(name=n, domain=d) for n, d in SPECIALTIES)
    existing = {p.code: p for p in db.scalars(select(Plan)).all()}
    for values in PLANS:
        plan = existing.get(values["code"])
        if plan is None:
            db.add(Plan(**values))
        else:
            for key, value in values.items():
                setattr(plan, key, value)
    for plan in existing.values():
        if plan.code not in {p["code"] for p in PLANS}:
            plan.active = False
    if not get_setting(db, "terms_version"):
        set_setting(db, "terms_version", "1.0")
    db.commit()


def ensure_admin(db: Session):
    if settings.admin_email and settings.admin_password and not db.scalar(select(User).where(User.email == settings.admin_email.lower())):
        db.add(User(email=settings.admin_email.lower(), password_hash=hash_password(settings.admin_password),
                    full_name="Administrateur AgriConnect", role="admin", status="active", terms_accepted_at=now()))
        db.commit()


def _user(db, email, name, role):
    u = User(email=f"{email}@{DEMO_DOMAIN}", password_hash=hash_password(DEMO_PASSWORD), full_name=name, role=role,
             status="active", terms_accepted_at=now())
    db.add(u); db.flush()
    return u


def _org(db, u, kind, name, status="validated", **kw):
    o = Organization(owner_id=u.id, kind=kind, name=name, status=status, country="Bénin", **kw)
    db.add(o); db.flush()
    return o


def _subscribe(db, org, plan_code, days=365):
    plan = db.scalar(select(Plan).where(Plan.code == plan_code))
    today = date.today()
    s = Subscription(org_id=org.id, plan_id=plan.id, status="active", start_date=today - timedelta(days=3), end_date=today + timedelta(days=days - 3))
    db.add(s); db.flush()
    inv = Invoice(org_id=org.id, subscription_id=s.id, description=f"Accès {plan.name}", amount_xof=plan.price_xof, status="paid", paid_at=now())
    db.add(inv); db.flush()
    inv.number = f"AC-{today.year}-{inv.id:05d}"
    db.add(Payment(invoice_id=inv.id, org_id=org.id, provider="demo", mode="demo", reference=f"AGRI-{org.id}-{plan.code}".upper(),
                   amount_xof=plan.price_xof, status="succeeded", paid_at=now()))
    return s


def seed_demo(db: Session) -> dict:
    """Jeu de données FICTIF pour tester chaque rôle. Idempotent. Retourne la liste des comptes."""
    if db.scalar(select(User).where(User.email == f"etablissement@{DEMO_DOMAIN}")):
        return {"already": True}
    seed_reference(db)
    lv = {l.code: l for l in db.scalars(select(DegreeLevel)).all()}
    sp = {s.name: s for s in db.scalars(select(Specialty)).all()}

    inst_u = _user(db, "etablissement", "Responsable partenariats", "institution")
    inst = _org(db, inst_u, "institution", "Institut Agricole Exemple", city="Abomey-Calavi", annual_quota=60,
                description="Établissement partenaire fictif.")
    _user(db, "etablissement.attente", "Établissement en attente", "institution")
    db.add(Organization(owner_id=db.scalar(select(User.id).where(User.email == f"etablissement.attente@{DEMO_DOMAIN}")),
                        kind="institution", name="École en attente de validation", status="pending", country="Bénin"))

    c1 = _org(db, _user(db, "entreprise.pro", "RH AgroVert", "company"), "company", "AgroVert Bénin SARL", city="Cotonou",
              sector="Production végétale", description="Entreprise fictive abonnée Professional.")
    c2 = _org(db, _user(db, "entreprise.starter", "RH Ferme du Mono", "company"), "company", "Ferme du Mono", city="Lokossa", sector="Élevage")
    _org(db, _user(db, "entreprise.attente", "Entreprise en attente", "company"), "company", "Nouvelle Agro (en attente)", status="pending")
    _org(db, _user(db, "entreprise.sansabo", "Entreprise sans abonnement", "company"), "company", "Transfo Sans Abonnement", city="Parakou")
    _subscribe(db, c1, "business"); _subscribe(db, c2, "business")

    people = [  # email, nom, titre diplôme, niveau, spécialité, année, lieu, dispo, compétences vérifiées, autres, expériences (rôle, org, début, fin)
        ("diplome.deat", "Akouavi Dossou", "DEAT en production végétale", "TECH", "Production végétale", 2023, "Abomey-Calavi", "available",
         ["Irrigation", "Gestion des sols"], ["Maraîchage"], [("Technicien stagiaire", "Coopérative Verdure", date(2023, 3, 1), date(2024, 2, 1))]),
        ("diplome.licence", "Koffi Adjovi", "Licence professionnelle en agroéconomie", "LIC_PRO", "Agroéconomie", 2024, "Cotonou", "available",
         ["Analyse de filières"], ["Excel", "Enquêtes terrain"], []),
        ("diplome.ingenieur", "Fatoumata Bio", "Diplôme d'ingénieur agronome", "INGENIEUR", "Production végétale", 2019, "Parakou", "employed_open",
         ["Irrigation", "Gestion de projet"], ["SIG"], [("Ingénieure terrain", "Projet Coton Nord", date(2019, 9, 1), date(2023, 8, 1)), ("Cheffe de projet adjointe", "ONG Terres Vives", date(2023, 9, 1), None)]),
        ("diplome.bts", "Ibrahim Séïdou", "BTS en production animale", "BTS_DUT", "Production animale", 2022, "Lokossa", "available",
         ["Alimentation du bétail"], ["Santé animale de base"], [("Assistant d'élevage", "Ferme du Mono", date(2022, 10, 1), date(2024, 4, 1))]),
        ("diplome.master", "Chantal Houngbo", "Master en transformation agroalimentaire", "MASTER", "Transformation agroalimentaire", 2021, "Cotonou", "temporary_mission",
         ["HACCP"], ["Qualité"], [("Responsable qualité junior", "Agro-Transfo SA", date(2021, 11, 1), date(2025, 1, 1))]),
        ("diplome.indisponible", "Raïssa Tossou", "Licence académique en gestion des ressources naturelles", "LIC_ACAD", "Gestion des ressources naturelles", 2023, "Porto-Novo", "unavailable", [], ["SIG"], []),
    ]
    profiles = {}
    for email, name, title, lvl, spec, year, loc, avail, vskills, oskills, exps in people:
        u = _user(db, email, name, "graduate")
        p = GraduateProfile(user_id=u.id, institution_id=inst.id, origin="institution", headline=title, location=loc, availability=avail,
                            visible=True, show_contact=(email == "diplome.ingenieur"), matching_opt_in=True, matching_consent_at=now(),
                            bio="Profil fictif.")
        db.add(p); db.flush()
        db.add(Degree(graduate_id=p.id, title=title, level_id=lv[lvl].id, specialty_id=sp[spec].id, specialty_text=spec, institution_name=inst.name,
                      year=year, status="verified", source="institution"))
        db.add_all(Skill(graduate_id=p.id, name=s, verified=True) for s in vskills)
        db.add_all(Skill(graduate_id=p.id, name=s, verified=False) for s in oskills)
        for role, org, s, e in exps:
            db.add(Experience(graduate_id=p.id, kind="job", organization=org, role=role, start_date=s, end_date=e, status="verified"))
        if email == "diplome.licence":  # un diplôme déclaré, non vérifié, pour illustrer l'avertissement
            db.add(Degree(graduate_id=p.id, title="Master en développement rural (en cours de vérification)", level_id=lv["MASTER"].id,
                          specialty_id=sp["Développement rural"].id, year=2025, status="in_review", source="self"))
        db.add(Achievement(graduate_id=p.id, title="Projet de fin d'études", year=year)) if email == "diplome.deat" else None
        profiles[email] = (u, p)
    db.flush()

    # compte en attente d'activation (créé « par l'administration »)
    u, link = create_graduate_account(db, full_name="Candidat En Attente", email=f"diplome.attente@{DEMO_DOMAIN}", phone="", institution_id=inst.id,
                                      degree_title="DEAT en production végétale", level_id=lv["TECH"].id, specialty_text="Production végétale",
                                      year=2025, honors="", country="Bénin", institution_name=inst.name)

    # offres de l'entreprise Pro
    def offer(title, level, **kw):
        o = Opportunity(org_id=c1.id, title=title, description="Offre de recrutement. " + title, type=kw.pop("type", "job"),
                        degree_level_id=lv[level].id, status="published", **kw)
        db.add(o); db.flush(); return o
    o1 = offer("Technicien agricole — DEAT en production végétale obligatoire", "TECH", specialty_id=sp["Production végétale"].id, specialty_required=True,
               min_experience_years=1, required_skills="Irrigation, Gestion des sols", desired_skills="Maraîchage", location="Abomey-Calavi", contract_type="CDD", sector="Production végétale")
    o2 = offer("Assistant en agroéconomie — Licence souhaitée, débutants acceptés", "LIC_PRO", degree_mandatory=False, specialty_id=sp["Agroéconomie"].id,
               required_skills="Analyse de filières", desired_skills="Excel", location="Cotonou", contract_type="CDI", sector="Économie")
    o3 = offer("Chargé de projet — ingénieur agronome", "INGENIEUR", allow_higher=True, min_experience_years=3, experience_mandatory=True,
               required_skills="Gestion de projet", location="Parakou", contract_type="CDI")
    o2.status = "published"

    # Les offres prépubliées disposent aussi d'un snapshot : le compte diplômé peut
    # tester « Mes correspondances » immédiatement, sans devoir republier l'offre.
    demo_offers = (o1, o2, o3)
    weights = match_weights(db)
    for demo_offer in demo_offers:
        scored = [(profile, match(offer_criteria(demo_offer), candidate_data(profile), weights))
                  for _, profile in profiles.values()]
        scored.sort(key=lambda item: (-item[1]["score"], item[0].id))
        scored = [(profile, result) for profile, result in scored if result["score"] > 0]
        total = len(scored)
        previous_score, rank = None, 0
        for index, (profile, result) in enumerate(scored, 1):
            if result["score"] != previous_score:
                rank, previous_score = index, result["score"]
            db.add(OfferMatch(opportunity_id=demo_offer.id, graduate_id=profile.id, score=result["score"], rank=rank,
                              total=total, criteria_json=json.dumps(result["criteria"], ensure_ascii=False), algorithm_version="1.0"))

    # une candidature, une collaboration vérifiée + évaluation + recommandation
    a = Application(opportunity_id=o1.id, graduate_id=profiles["diplome.deat"][0].id, cover_letter="Candidature fictive.", status="submitted")
    db.add(a); db.flush()
    db.add(ApplicationEvent(application_id=a.id, status="submitted", actor_id=a.graduate_id))
    ing = profiles["diplome.ingenieur"][1]
    col = Collaboration(company_id=c1.id, graduate_id=ing.id, kind="job", title="Ingénieure terrain", start_date=date(2022, 1, 1), end_date=date(2023, 6, 30), status="verified")
    db.add(col); db.flush()
    db.add(Evaluation(collaboration_id=col.id, company_id=c1.id, graduate_id=ing.id, technical=5, deadlines=4, adaptability=5, professionalism=5, teamwork=4, results=5,
                      comment="Évaluation factuelle."))
    db.add(Recommendation(collaboration_id=col.id, company_id=c1.id, graduate_id=ing.id, text="Recommandation fictive : rigoureuse, autonome, très bonne communication."))
    col2 = Collaboration(company_id=c1.id, graduate_id=profiles["diplome.bts"][1].id, kind="internship", title="Stage d'élevage", start_date=date(2024, 1, 1), end_date=date(2024, 3, 31), status="pending")
    db.add(col2)

    # liste transmise par l'établissement (à traiter par l'administration)
    lst = SubmittedList(institution_id=inst.id, title="Promotion 2026 — liste test", academic_year="2025-2026", filename="promotion_2026.csv", status="received")
    db.add(lst); db.flush()
    rows = [("Yao Kpodo", f"yao.kpodo@{DEMO_DOMAIN}", "DEAT en production végétale", "TECH", "Production végétale", 2026, "pending", ""),
            ("Mireille Sagbo", f"mireille.sagbo@{DEMO_DOMAIN}", "BTS en agroalimentaire", "BTS_DUT", "Transformation agroalimentaire", 2026, "pending", ""),
            ("Sans Email", "pas-un-email", "Licence professionnelle", "LIC_PRO", "", 2026, "invalid", "Email invalide"),
            ("Doublon Existant", f"diplome.deat@{DEMO_DOMAIN}", "DEAT", "TECH", "", 2026, "invalid", "Un compte existe déjà pour cet email")]
    for i, (n, e, d, l, s, y, st, m) in enumerate(rows, start=2):
        db.add(SubmittedRow(list_id=lst.id, line_no=i, full_name=n, email=e, degree_title=d, level_code=l, specialty=s, year=y, status=st, message=m))
    set_setting(db, "demo_data", "true")
    db.commit()
    return {"already": False, "invitation_link_demo": link}


DEMO_ACCOUNTS = [
    ("Administrateur", "(ADMIN_EMAIL de votre .env)", "(ADMIN_PASSWORD de votre .env)"),
    ("Établissement validé", f"etablissement@{DEMO_DOMAIN}", DEMO_PASSWORD),
    ("Établissement en attente de validation", f"etablissement.attente@{DEMO_DOMAIN}", DEMO_PASSWORD),
    ("Entreprise abonnée Professional", f"entreprise.pro@{DEMO_DOMAIN}", DEMO_PASSWORD),
    ("Entreprise abonnée Starter", f"entreprise.starter@{DEMO_DOMAIN}", DEMO_PASSWORD),
    ("Entreprise validée, sans abonnement", f"entreprise.sansabo@{DEMO_DOMAIN}", DEMO_PASSWORD),
    ("Entreprise en attente de validation", f"entreprise.attente@{DEMO_DOMAIN}", DEMO_PASSWORD),
    ("Diplômé DEAT", f"diplome.deat@{DEMO_DOMAIN}", DEMO_PASSWORD),
    ("Diplômé Licence", f"diplome.licence@{DEMO_DOMAIN}", DEMO_PASSWORD),
    ("Diplômée Ingénieur", f"diplome.ingenieur@{DEMO_DOMAIN}", DEMO_PASSWORD),
    ("Diplômé BTS", f"diplome.bts@{DEMO_DOMAIN}", DEMO_PASSWORD),
    ("Diplômée Master", f"diplome.master@{DEMO_DOMAIN}", DEMO_PASSWORD),
    ("Diplômée indisponible", f"diplome.indisponible@{DEMO_DOMAIN}", DEMO_PASSWORD),
]
