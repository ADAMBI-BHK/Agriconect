"""Score de correspondance profil ↔ offre. Fonctions pures, sans base de données.

Principes (cahier des charges §8 et §10) :
- le niveau de diplôme, la spécialité, l'expérience et les compétences sont des critères DISTINCTS ;
- le score de correspondance n'est PAS un score de réputation et n'est pas une probabilité d'embauche ;
- aucun candidat n'est exclu automatiquement : un critère obligatoire manquant est signalé (``blocking``) ;
- chaque critère est expliqué (satisfait / partiel / manquant / à vérifier / non exigé).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from .text import norm

DEFAULT_WEIGHTS = {"degree": 30, "specialty": 20, "skills": 25, "experience": 15, "location": 5, "availability": 5}
LABELS = {"degree": "Niveau de diplôme", "specialty": "Spécialité", "skills": "Compétences",
          "experience": "Expérience", "location": "Localisation", "availability": "Disponibilité"}
AVAILABILITY_CREDIT = {"available": 1.0, "employed_open": 0.8, "temporary_mission": 0.6, "unavailable": 0.0}
AVAILABILITY_LABEL = {"available": "Disponible", "employed_open": "En poste, ouvert aux propositions",
                      "temporary_mission": "En mission temporaire", "unavailable": "Non disponible"}


@dataclass
class DegreeInfo:
    title: str
    level_code: str
    level_rank: int
    specialty: str | None = None
    domain: str | None = None
    status: str = "declared"  # declared|in_review|verified|rejected|to_complete


@dataclass
class CandidateData:
    degrees: list[DegreeInfo] = field(default_factory=list)
    skills: set[str] = field(default_factory=set)  # noms normalisés
    experience_years: float = 0.0
    location: str = ""
    availability: str = "available"


@dataclass
class OfferCriteria:
    level_code: str
    level_rank: int
    degree_mandatory: bool = True
    accepted_level_codes: list[str] = field(default_factory=list)
    accepted_titles: list[str] = field(default_factory=list)
    allow_higher: bool = True
    allow_lower_alt: bool = False
    specialty: str | None = None
    specialty_domain: str | None = None
    specialty_required: bool = False
    min_experience_years: float = 0.0
    experience_mandatory: bool = False
    required_skills: list[str] = field(default_factory=list)
    desired_skills: list[str] = field(default_factory=list)
    location: str = ""


def _crit(key, ratio, status, detail, applicable=True, blocking=False):
    return {"key": key, "label": LABELS[key], "ratio": ratio, "status": status, "detail": detail,
            "applicable": applicable, "blocking": blocking}


def _degree_one(offer: OfferCriteria, d: DegreeInfo):
    """Évalue UN diplôme : (ratio, statut, détail). Les équivalences ne sont jamais présumées."""
    titles = [norm(t) for t in offer.accepted_titles]
    if d.title and any(t and t in norm(d.title) for t in titles):
        return 1.0, "met", f"« {d.title} » figure parmi les intitulés acceptés"
    if d.level_code in offer.accepted_level_codes:
        return 1.0, "met", f"Niveau « {d.level_code} » accepté explicitement par l'entreprise"
    if d.level_rank == offer.level_rank:
        return 1.0, "met", "Niveau requis atteint"
    if d.level_rank > offer.level_rank:
        if offer.allow_higher:
            return 1.0, "met", "Niveau supérieur au minimum requis (accepté)"
        return 0.0, "missing", "Niveau supérieur non accepté pour ce poste (restriction de l'entreprise)"
    if offer.allow_lower_alt:
        return 0.5, "partial", "Niveau inférieur au minimum : alternative autorisée par l'entreprise"
    return 0.0, "missing", "Niveau inférieur au minimum requis"


def _degree(offer: OfferCriteria, cand: CandidateData):
    if not cand.degrees:
        return _crit("degree", 0.0, "missing", "Aucun diplôme enregistré", blocking=offer.degree_mandatory)
    usable = [d for d in cand.degrees if d.status != "rejected"] or []
    if not usable:
        return _crit("degree", 0.0, "missing", "Aucun diplôme non rejeté", blocking=offer.degree_mandatory)
    best = max(((*_degree_one(offer, d), d) for d in usable), key=lambda x: (x[0], x[3].status == "verified"))
    ratio, status, detail, d = best
    if ratio > 0 and d.status != "verified":
        detail += f" — diplôme « {d.title} » NON vérifié (statut : {d.status})"
        status = "to_verify"
    elif ratio > 0:
        detail += f" — « {d.title} » (vérifié)"
    return _crit("degree", ratio, status, detail, blocking=(ratio == 0 and offer.degree_mandatory))


def _specialty(offer: OfferCriteria, cand: CandidateData):
    if not offer.specialty:
        return _crit("specialty", 1.0, "na", "Aucune spécialité exigée", applicable=False)
    want, dom = norm(offer.specialty), norm(offer.specialty_domain or "")
    if any(d.specialty and norm(d.specialty) == want for d in cand.degrees if d.status != "rejected"):
        return _crit("specialty", 1.0, "met", f"Spécialité « {offer.specialty} » trouvée")
    if dom and any(d.domain and norm(d.domain) == dom for d in cand.degrees if d.status != "rejected"):
        return _crit("specialty", 0.5, "partial", f"Même domaine (« {offer.specialty_domain} ») mais spécialité différente")
    return _crit("specialty", 0.0, "missing", f"Spécialité « {offer.specialty} » absente", blocking=offer.specialty_required)


def _skills(offer: OfferCriteria, cand: CandidateData):
    req, des = [norm(s) for s in offer.required_skills], [norm(s) for s in offer.desired_skills]
    if not req and not des:
        return _crit("skills", 1.0, "na", "Aucune compétence exigée", applicable=False)
    have_req = [s for s in req if s in cand.skills]
    have_des = [s for s in des if s in cand.skills]
    r_req = len(have_req) / len(req) if req else 1.0
    r_des = len(have_des) / len(des) if des else 1.0
    ratio = (0.7 * r_req + 0.3 * r_des) if (req and des) else (r_req if req else r_des)
    miss = [s for s in offer.required_skills if norm(s) not in cand.skills]
    parts = []
    if req:
        parts.append(f"obligatoires {len(have_req)}/{len(req)}")
    if des:
        parts.append(f"souhaitées {len(have_des)}/{len(des)}")
    detail = "Compétences " + ", ".join(parts) + (f" — manquantes : {', '.join(miss)}" if miss else "")
    status = "met" if ratio >= 0.999 else ("partial" if ratio > 0 else "missing")
    return _crit("skills", ratio, status, detail)


def _experience(offer: OfferCriteria, cand: CandidateData):
    need = offer.min_experience_years
    if need <= 0:
        return _crit("experience", 1.0, "na", "Aucune expérience minimale exigée", applicable=False)
    y = cand.experience_years
    if y >= need:
        return _crit("experience", 1.0, "met", f"{y:.1f} an(s) d'expérience (minimum {need:g})")
    ratio = max(0.0, min(1.0, y / need))
    return _crit("experience", ratio, "partial" if y > 0 else "missing",
                 f"{y:.1f} an(s) d'expérience pour {need:g} exigé(s)", blocking=offer.experience_mandatory)


def _location(offer: OfferCriteria, cand: CandidateData):
    if not offer.location:
        return _crit("location", 1.0, "na", "Aucune localisation précisée", applicable=False)
    if norm(offer.location) == norm(cand.location):
        return _crit("location", 1.0, "met", f"Même commune ({offer.location})")
    return _crit("location", 0.0, "missing", f"Commune du poste : {offer.location} ; candidat : {cand.location or 'non renseignée'} (la mobilité n'est pas connue)")


def _availability(cand: CandidateData):
    r = AVAILABILITY_CREDIT.get(cand.availability, 0.0)
    st = "met" if r >= 1 else ("partial" if r > 0 else "missing")
    return _crit("availability", r, st, AVAILABILITY_LABEL.get(cand.availability, cand.availability))


def match(offer: OfferCriteria, cand: CandidateData, weights: dict | None = None) -> dict:
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    crits = [_degree(offer, cand), _specialty(offer, cand), _skills(offer, cand),
             _experience(offer, cand), _location(offer, cand), _availability(cand)]
    for c in crits:
        c["weight"] = w[c["key"]]
    applicable = [c for c in crits if c["applicable"]]
    total_w = sum(c["weight"] for c in applicable)
    score = round(100 * sum(c["weight"] * c["ratio"] for c in applicable) / total_w) if total_w else 0
    blocking = [c["label"] for c in crits if c["blocking"]]
    return {"score": score, "criteria": crits, "blocking_missing": blocking,
            "to_verify": [c["label"] for c in crits if c["status"] == "to_verify"],
            "note": "Score de correspondance : adéquation à cette offre uniquement. Ce n'est ni la réputation ni une probabilité d'embauche."}


# ------------------------------------------------------------------ expérience
def experience_years(periods: list[tuple[date, date | None]], today: date | None = None) -> float:
    """Durée cumulée en années, sans double comptage des périodes qui se chevauchent."""
    today = today or date.today()
    spans = sorted((s, min(e or today, today)) for s, e in periods if s <= today)
    merged: list[list[date]] = []
    for s, e in spans:
        if e < s:
            continue
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return round(sum((e - s).days for s, e in merged) / 365.25, 2)


def experience_category(years: float) -> str:
    """Catégories indicatives du cahier des charges §7 (seuils à adapter aux métiers)."""
    if years < 1:
        return "Jeune diplômé"
    if years < 3:
        return "Début de carrière"
    if years <= 5:
        return "Professionnel expérimenté"
    return "Expert / senior"
