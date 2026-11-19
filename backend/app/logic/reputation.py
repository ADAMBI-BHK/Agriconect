"""Score de réputation (hypothèse de départ à calibrer — cahier des charges §10.3). Fonctions pures.

Pondérations par défaut : évaluations vérifiées 50 %, compétences vérifiées 25 %, formation et sélection 15 %,
réalisations et recommandations 10 %. Le NIVEAU de diplôme n'entre PAS dans ce score (il reste affiché à part).
"""
from __future__ import annotations
from datetime import date

DEFAULT_WEIGHTS = {"evaluations": 50, "skills": 25, "formation": 15, "achievements": 10}
PRIOR_MEAN, PRIOR_WEIGHT = 3.5, 1.5  # lissage : une note isolée ne détruit pas un profil


def reputation_score(evals: list[tuple[float, date]], skills_verified: int, skills_total: int,
                     has_verified_degree: bool, selected_by_institution: bool,
                     achievements: int, recommendations: int,
                     today: date | None = None, weights: dict | None = None) -> dict:
    today = today or date.today()
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    # évaluations : moyenne pondérée par la récence (demi-vie 2 ans) et lissée vers la moyenne a priori
    if evals:
        num = PRIOR_MEAN * PRIOR_WEIGHT
        den = PRIOR_WEIGHT
        for avg, d in evals:
            age = max(0.0, (today - d).days / 365.25)
            wt = 0.5 ** (age / 2)
            num += avg * wt
            den += wt
        ev = ((num / den) - 1) / 4
    else:
        ev = None
    sk = (skills_verified / skills_total) if skills_total else 0.0
    fo = 0.6 * has_verified_degree + 0.4 * selected_by_institution
    ac = min(1.0, (achievements + recommendations) / 3)
    comps = {"skills": sk, "formation": fo, "achievements": ac}
    if ev is not None:
        comps["evaluations"] = ev
    tw = sum(w[k] for k in comps)
    score = round(100 * sum(w[k] * v for k, v in comps.items()) / tw) if tw else 0
    return {"score": score, "provisional": ev is None, "evaluations_count": len(evals),
            "components": {k: round(v, 3) for k, v in comps.items()},
            "note": ("Score provisoire : aucune évaluation vérifiée pour le moment (formation, compétences et réalisations uniquement)."
                     if ev is None else "Calculé à partir d'évaluations liées à des collaborations vérifiées.")}
