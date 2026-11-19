"""Tests de la logique pure (sans FastAPI ni base de données) : matching, réputation, droits, import."""
import io, unittest
from datetime import date
from app.logic.matching import (DegreeInfo, CandidateData, OfferCriteria, match, experience_years, experience_category)
from app.logic.reputation import reputation_score
from app.logic.entitlements import quota_allows, quota_left, subscription_is_current, extend_end, month_key
from app.logic.importer import parse_rows, ImportError_
from app.logic.text import norm

LOOKUP = {norm(k): v for k, v in {"TECH": "TECH", "DEAT": "TECH", "BTS": "BTS_DUT", "Licence professionnelle": "LIC_PRO",
                                  "LIC_PRO": "LIC_PRO", "Master": "MASTER"}.items()}


def offer(**kw):
    base = dict(level_code="TECH", level_rank=1, specialty="Production végétale", specialty_domain="Agriculture")
    base.update(kw)
    return OfferCriteria(**base)


def cand(rank=1, code="TECH", status="verified", spec="Production végétale", **kw):
    d = DegreeInfo("DEAT en production végétale", code, rank, spec, "Agriculture", status)
    return CandidateData(degrees=[d], **kw)


class Matching(unittest.TestCase):
    def crit(self, r, key):
        return next(c for c in r["criteria"] if c["key"] == key)

    def test_exact_level_met(self):
        r = match(offer(), cand(skills=set()))
        self.assertEqual(self.crit(r, "degree")["status"], "met")
        self.assertEqual(r["blocking_missing"], [])

    def test_lower_mandatory_is_blocking_not_excluded(self):
        r = match(offer(level_code="LIC_PRO", level_rank=3), cand())
        self.assertEqual(self.crit(r, "degree")["status"], "missing")
        self.assertIn("Niveau de diplôme", r["blocking_missing"])
        self.assertIsInstance(r["score"], int)  # jamais exclu : un score est toujours produit

    def test_lower_alternative_only_if_authorized(self):
        r = match(offer(level_code="LIC_PRO", level_rank=3, allow_lower_alt=True), cand())
        self.assertEqual(self.crit(r, "degree")["status"], "partial")
        self.assertEqual(r["blocking_missing"], [])

    def test_higher_accepted_unless_restricted(self):
        c = cand(rank=4, code="MASTER")
        self.assertEqual(self.crit(match(offer(), c), "degree")["status"], "met")
        r = match(offer(allow_higher=False), c)
        self.assertEqual(self.crit(r, "degree")["status"], "missing")

    def test_accepted_title_overrides_level(self):
        r = match(offer(level_code="MASTER", level_rank=4, accepted_titles=["DEAT"]), cand())
        self.assertEqual(self.crit(r, "degree")["status"], "met")

    def test_unverified_degree_flagged(self):
        r = match(offer(), cand(status="declared"))
        self.assertEqual(self.crit(r, "degree")["status"], "to_verify")
        self.assertIn("Niveau de diplôme", r["to_verify"])

    def test_rejected_degree_ignored(self):
        r = match(offer(), cand(status="rejected"))
        self.assertEqual(self.crit(r, "degree")["status"], "missing")

    def test_specialty_domain_partial(self):
        other = DegreeInfo("DEAT élevage", "TECH", 1, "Élevage", "Élevage", "verified")
        r = match(offer(), CandidateData(degrees=[other]))
        self.assertEqual(self.crit(r, "specialty")["status"], "missing")
        d = DegreeInfo("DEAT", "TECH", 1, "Horticulture", "Agriculture", "verified")
        r = match(offer(), CandidateData(degrees=[d]))
        self.assertEqual(self.crit(r, "specialty")["status"], "partial")

    def test_skills_accent_insensitive_and_missing_listed(self):
        r = match(offer(required_skills=["Irrigation", "Gestion des sols"]), cand(skills={"irrigation"}))
        c = self.crit(r, "skills")
        self.assertEqual(c["status"], "partial")
        self.assertIn("Gestion des sols", c["detail"])
        r2 = match(offer(required_skills=["Élevage"]), cand(skills={norm("élevage")}))
        self.assertEqual(self.crit(r2, "skills")["status"], "met")

    def test_experience_separate_from_degree(self):
        o = offer(min_experience_years=2, experience_mandatory=True)
        r = match(o, cand(experience_years=0.5))
        self.assertEqual(self.crit(r, "degree")["status"], "met")
        self.assertEqual(self.crit(r, "experience")["status"], "partial")
        self.assertIn("Expérience", r["blocking_missing"])

    def test_not_applicable_criteria_excluded_from_score(self):
        r = match(OfferCriteria(level_code="TECH", level_rank=1), cand(spec=None))
        self.assertEqual(r["score"], 100)

    def test_unavailable_lowers_score(self):
        a = match(offer(), cand(availability="available"))["score"]
        b = match(offer(), cand(availability="unavailable"))["score"]
        self.assertGreater(a, b)

    def test_custom_weights(self):
        r = match(offer(required_skills=["x"]), cand(), weights={"skills": 0})
        self.assertEqual(self.crit(r, "skills")["weight"], 0)

    def test_experience_years_merges_overlaps(self):
        p = [(date(2020, 1, 1), date(2021, 1, 1)), (date(2020, 6, 1), date(2021, 6, 1))]
        self.assertAlmostEqual(experience_years(p, date(2022, 1, 1)), 1.42, delta=0.02)  # 1er janv. 2020 → 1er juin 2021
        self.assertAlmostEqual(experience_years([(date(2024, 1, 1), None)], date(2025, 1, 1)), 1.0, delta=0.02)

    def test_experience_categories(self):
        self.assertEqual(experience_category(0), "Jeune diplômé")
        self.assertEqual(experience_category(1.5), "Début de carrière")
        self.assertEqual(experience_category(4), "Professionnel expérimenté")
        self.assertEqual(experience_category(7), "Expert / senior")


class Reputation(unittest.TestCase):
    D = date(2026, 11, 17)

    def test_no_evals_is_provisional(self):
        r = reputation_score([], 0, 0, True, True, 0, 0, self.D)
        self.assertTrue(r["provisional"])
        self.assertNotIn("evaluations", r["components"])

    def test_single_bad_rating_does_not_destroy(self):
        r = reputation_score([(1.0, self.D)], 2, 2, True, True, 2, 1, self.D)
        self.assertGreater(r["score"], 40)

    def test_more_good_evals_raise_score(self):
        one = reputation_score([(5.0, self.D)], 1, 2, True, True, 1, 0, self.D)["score"]
        many = reputation_score([(5.0, self.D)] * 5, 1, 2, True, True, 1, 0, self.D)["score"]
        self.assertGreater(many, one)

    def test_degree_level_not_an_input(self):
        import inspect
        self.assertNotIn("level", " ".join(inspect.signature(reputation_score).parameters))

    def test_recency(self):
        old = reputation_score([(5.0, date(2016, 1, 1))], 0, 0, False, False, 0, 0, self.D)["score"]
        new = reputation_score([(5.0, self.D)], 0, 0, False, False, 0, 0, self.D)["score"]
        self.assertGreater(new, old)


class Entitlements(unittest.TestCase):
    def test_quota(self):
        self.assertTrue(quota_allows(None, 999))
        self.assertTrue(quota_allows(3, 2))
        self.assertFalse(quota_allows(3, 3))
        self.assertEqual(quota_left(3, 5), 0)
        self.assertIsNone(quota_left(None, 5))

    def test_current_subscription(self):
        d = date(2026, 11, 17)
        self.assertTrue(subscription_is_current("active", date(2026, 11, 1), date(2026, 11, 30), d))
        self.assertFalse(subscription_is_current("active", date(2026, 10, 1), date(2026, 10, 31), d))
        self.assertFalse(subscription_is_current("pending_payment", date(2026, 11, 1), date(2026, 11, 30), d))
        self.assertFalse(subscription_is_current("active", None, None, d))

    def test_renewal_extends_from_end(self):
        d = date(2026, 11, 17)
        self.assertEqual(extend_end(date(2026, 11, 27), d, 30), date(2026, 12, 27))
        self.assertEqual(extend_end(date(2026, 10, 1), d, 30), date(2026, 12, 17))
        self.assertEqual(month_key(d), "2026-11")


class Importer(unittest.TestCase):
    H = "nom_complet;email;telephone;diplome;niveau;specialite;annee_obtention;mention;pays\n"

    def test_valid_and_invalid_rows(self):
        csv = (self.H + "Ama Koffi;ama@x.bj;;DEAT production végétale;DEAT;Production végétale;2025;Bien;Bénin\n"
               "X;pasunemail;;;Inconnu;;abc;;\n"
               "Dup;ama@x.bj;;D;BTS;;2024;;\n")
        rows = parse_rows("l.csv", csv.encode(), LOOKUP, today=date(2026, 11, 17))
        self.assertEqual(rows[0].errors, [])
        self.assertEqual(rows[0].data["level_code"], "TECH")
        self.assertTrue(any("Email invalide" in e for e in rows[1].errors))
        self.assertTrue(any("Niveau inconnu" in e for e in rows[1].errors))
        self.assertTrue(any("double" in e for e in rows[2].errors))

    def test_header_aliases_comma_and_accents(self):
        csv = "Nom,Courriel,Intitulé du diplôme,Niveau,Filière,Année\nAma Koffi,a@x.bj,Licence pro agro,Licence professionnelle,Agro,2024\n"
        rows = parse_rows("l.csv", csv.encode("utf-8"), LOOKUP, today=date(2026, 11, 17))
        self.assertEqual(rows[0].errors, [])
        self.assertEqual(rows[0].data["level_code"], "LIC_PRO")
        self.assertEqual(rows[0].data["year"], 2024)

    def test_missing_columns_and_empty_and_limits(self):
        with self.assertRaises(ImportError_):
            parse_rows("l.csv", b"nom;email\nA;b\n", LOOKUP)
        with self.assertRaises(ImportError_):
            parse_rows("l.csv", b"", LOOKUP)
        with self.assertRaises(ImportError_):
            parse_rows("l.pdf", b"x", LOOKUP)
        big = self.H + "".join(f"N{i} Nom;a{i}@x.bj;;D;BTS;;2024;;\n" for i in range(5))
        with self.assertRaises(ImportError_):
            parse_rows("l.csv", big.encode(), LOOKUP, max_rows=3)

    def test_xlsx(self):
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active
        ws.append(["nom_complet", "email", "diplome", "niveau", "annee_obtention"])
        ws.append(["Ama Koffi", "ama@x.bj", "BTS agro", "BTS", 2025])
        buf = io.BytesIO(); wb.save(buf)
        rows = parse_rows("l.xlsx", buf.getvalue(), LOOKUP, today=date(2026, 11, 17))
        self.assertEqual(rows[0].errors, [])
        self.assertEqual(rows[0].data["year"], 2025)
        with self.assertRaises(ImportError_):
            parse_rows("l.xlsx", b"pas un xlsx", LOOKUP)


if __name__ == "__main__":
    unittest.main()
