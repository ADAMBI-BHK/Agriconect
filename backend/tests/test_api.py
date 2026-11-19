"""Tests d'intégration des parcours (nécessitent fastapi, sqlalchemy, httpx, pytest installés : voir README).
Ils s'exécutent dans l'ordre : chaque classe construit l'état utilisé par la suivante (scénario complet)."""
import io
from datetime import date, timedelta
from tests.conftest import new_client, login

PWD = "Motdepasse1"
S = {}  # état partagé du scénario


def ref(c):
    return c.get("/api/referentials").json()


def level_id(c, code):
    return next(l["id"] for l in ref(c)["levels"] if l["code"] == code)


def spec_id(c, name):
    return next(s["id"] for s in ref(c)["specialties"] if s["name"] == name)


CSV = ("nom_complet;email;telephone;diplome;niveau;specialite;annee_obtention;mention;pays\n"
       "Ama Koffi;ama@etu.bj;;DEAT en production végétale;DEAT;Production végétale;2025;Bien;Bénin\n"
       "Bob Sossa;bob@etu.bj;;Licence professionnelle en agroéconomie;Licence professionnelle;Agroéconomie;2025;;Bénin\n"
       "Mauvais;pasunemail;;X;Inconnu;;2025;;Bénin\n")


# ------------------------------------------------------------------ sécurité de base
def test_csrf_header_required():
    from fastapi.testclient import TestClient
    from app.main import app
    assert TestClient(app).post("/api/auth/login", json={"email": "a@b.co", "password": "x"}).status_code == 403


def test_no_free_graduate_registration():
    c = new_client()
    r = c.post("/api/auth/register", json={"email": "x@y.bj", "password": PWD, "full_name": "X Y", "role": "graduate", "accept_terms": True})
    assert r.status_code in (404, 405)
    r = c.post("/api/auth/register-organization", json={"email": "x@y.bj", "password": PWD, "full_name": "X Y", "role": "graduate",
                                                          "org_name": "Z", "accept_terms": True})
    assert r.status_code == 422


def test_weak_password_rejected():
    r = new_client().post("/api/auth/register-organization", json={"email": "w@y.bj", "password": "abcdefgh", "full_name": "X Y", "role": "company",
                                                                    "org_name": "Z Corp", "accept_terms": True})
    assert r.status_code == 422


def test_password_reset_is_generic_and_one_time():
    from app import routes_auth
    from app.security import hash_token

    email = "reset@test.bj"
    old_password = "Ancien123"
    c = new_client()
    assert c.post("/api/auth/register-organization", json={"email": email, "password": old_password, "full_name": "Compte Reset", "role": "company",
                                                            "org_name": "Entreprise Reset", "accept_terms": True}).status_code == 201
    raw = "R" * 48
    original = routes_auth.new_reset_token
    routes_auth.new_reset_token = lambda: (raw, hash_token(raw))
    try:
        known = c.post("/api/auth/request-password-reset", json={"email": email})
        unknown = c.post("/api/auth/request-password-reset", json={"email": "inconnu@test.bj"})
        assert known.status_code == unknown.status_code == 200
        assert known.json()["message"] == unknown.json()["message"]
    finally:
        routes_auth.new_reset_token = original
    reset = new_client().post("/api/auth/reset-password", json={"token": raw, "new_password": "Nouveau123"})
    assert reset.status_code == 200
    assert new_client().post("/api/auth/reset-password", json={"token": raw, "new_password": "Encore123"}).status_code == 400
    assert new_client().post("/api/auth/login", json={"email": email, "password": old_password}).status_code == 401
    assert new_client().post("/api/auth/login", json={"email": email, "password": "Nouveau123"}).status_code == 200


# ------------------------------------------------------------------ parcours établissement + administration
class TestInstitutionAndAdmin:
    def test_institution_registers_pending(self):
        c = new_client()
        r = c.post("/api/auth/register-organization", json={"email": "inst@test.bj", "password": PWD, "full_name": "Resp Inst", "role": "institution",
                                                             "org_name": "Institut Test", "accept_terms": True})
        assert r.status_code == 201 and r.json()["org"]["status"] == "pending"
        assert c.post("/api/institution/lists", data={"title": "L1"}, files={"file": ("l.csv", CSV.encode(), "text/csv")}).status_code == 403  # non validé

    def test_admin_validates_institution(self, admin):
        orgs = admin.get("/api/admin/orgs?kind=institution&status=pending").json()
        oid = next(o["id"] for o in orgs if o["name"] == "Institut Test")
        S["inst_org"] = oid
        assert admin.post(f"/api/admin/orgs/{oid}/status", json={"status": "validated", "annual_quota": 100}).status_code == 200
        assert admin.post(f"/api/admin/orgs/{oid}/status", json={"status": "rejected"}).status_code == 422  # motif obligatoire

    def test_upload_list_and_status(self):
        c = login("inst@test.bj", PWD)
        r = c.post("/api/institution/lists", data={"title": "Promo 2025", "academic_year": "2024-2025"}, files={"file": ("l.csv", CSV.encode(), "text/csv")})
        assert r.status_code == 201, r.text
        d = r.json(); S["list"] = d["id"]
        assert d["counts"]["pending"] == 2 and d["counts"]["invalid"] == 1 and d["status"] == "received"
        assert c.post("/api/institution/lists", data={"title": "Mauvais"}, files={"file": ("x.pdf", b"%PDF", "application/pdf")}).status_code == 422
        assert c.get("/api/institution/lists/template.csv").status_code == 200

    def test_institution_cannot_create_accounts(self):
        c = login("inst@test.bj", PWD)
        assert c.post(f"/api/admin/lists/{S['list']}/create-accounts").status_code == 403
        assert c.get("/api/admin/users").status_code == 403

    def test_admin_reviews_and_creates_accounts(self, admin):
        lid = S["list"]
        assert any(l["id"] == lid for l in admin.get("/api/admin/lists").json())
        assert admin.post(f"/api/admin/lists/{lid}/validate-all").json()["validated"] == 2
        rows = admin.get(f"/api/admin/lists/{lid}").json()["rows"]
        bad = next(r for r in rows if r["status"] == "invalid")
        assert admin.post(f"/api/admin/lists/{lid}/rows/{bad['id']}/reject", json={"reason": "Email invalide"}).status_code == 200
        r = admin.post(f"/api/admin/lists/{lid}/create-accounts")
        assert r.status_code == 200, r.text
        inv = r.json()["invitations"]
        assert r.json()["created"] == 2 and all(i["link"] for i in inv)
        S["links"] = {i["email"]: i["link"] for i in inv}
        assert admin.get(f"/api/admin/lists/{lid}").json()["status"] == "partially_validated"
        assert admin.post(f"/api/admin/lists/{lid}/create-accounts").status_code == 409  # plus rien à créer

    def test_institution_sees_tracking_and_can_fix_rejected(self):
        c = login("inst@test.bj", PWD)
        cands = c.get("/api/institution/candidates").json()
        assert {x["status"] for x in cands} >= {"account_created", "rejected"}
        rej = next(x for x in cands if x["status"] == "rejected")
        r = c.put(f"/api/institution/lists/{S['list']}/rows/{rej['id']}", json={"full_name": "Corrigé Bien", "email": "corrige@etu.bj", "degree_title": "BTS agro",
                                                                                 "level_code": "BTS_DUT", "year": 2025})
        assert r.status_code == 200 and r.json()["status"] == "pending"
        st = c.get("/api/institution/stats").json()
        assert st["accounts_created"] == 2 and st["accounts_activated"] == 0


# ------------------------------------------------------------------ parcours candidat
class TestGraduate:
    def test_cannot_login_before_activation(self):
        r = new_client().post("/api/auth/login", json={"email": "ama@etu.bj", "password": PWD})
        assert r.status_code == 401

    def test_activation_requires_terms_and_valid_token(self):
        c = new_client()
        token = S["links"]["ama@etu.bj"].split("token=")[1]
        assert c.post("/api/auth/activate", json={"token": token, "password": PWD, "accept_terms": False}).status_code == 422
        assert c.post("/api/auth/activate", json={"token": "x" * 40, "password": PWD, "accept_terms": True}).status_code == 404
        assert c.get(f"/api/auth/activation-info?token={token}").json()["email"] == "ama@etu.bj"
        r = c.post("/api/auth/activate", json={"token": token, "password": PWD, "accept_terms": True})
        assert r.status_code == 200 and r.json()["role"] == "graduate"
        assert c.post("/api/auth/activate", json={"token": token, "password": PWD, "accept_terms": True}).status_code == 404  # lien à usage unique
        # le second candidat reste en attente
        bob = S["links"]["bob@etu.bj"].split("token=")[1]
        assert new_client().post("/api/auth/activate", json={"token": bob, "password": PWD, "accept_terms": True}).status_code == 200

    def test_complete_profile(self):
        c = login("ama@etu.bj", PWD)
        p = c.get("/api/graduate/profile").json()
        assert p["degrees"][0]["status"] == "verified" and p["degrees"][0]["level"]["code"] == "TECH"
        assert c.put("/api/graduate/profile", json={"headline": "Technicienne agricole", "bio": "Passionnée", "location": "Abomey-Calavi",
                                                     "availability": "available", "visible": True, "show_contact": False}).status_code == 200
        assert c.put("/api/graduate/profile", json={"location": "Atlantis"}).status_code == 422
        for s in ("Irrigation", "Gestion des sols"):
            assert c.post("/api/graduate/skills", json={"name": s}).status_code == 201
        assert c.post("/api/graduate/skills", json={"name": "irrigation"}).status_code == 409
        today = date.today()
        r = c.post("/api/graduate/experiences", json={"kind": "internship", "organization": "Coop Verdure", "role": "Stagiaire",
                                                       "start_date": (today - timedelta(days=500)).isoformat(), "end_date": (today - timedelta(days=130)).isoformat()})
        assert r.status_code == 201
        assert c.post("/api/graduate/experiences", json={"organization": "X Y", "role": "Z Z", "start_date": (today + timedelta(days=5)).isoformat()}).status_code == 422
        d = c.post("/api/graduate/degrees", json={"title": "Licence pro (déclarée)", "level_id": level_id(c, "LIC_PRO"), "year": 2026})
        assert d.status_code == 201 and d.json()["status"] == "declared"
        inst_degree = c.get("/api/graduate/profile").json()["degrees"][0]
        assert c.delete(f"/api/graduate/degrees/{inst_degree['id']}").status_code == 409  # diplôme vérifié non supprimable
        assert 0 < c.get("/api/graduate/profile").json()["completeness"] <= 100

    def test_cv_upload_validation(self):
        c = login("ama@etu.bj", PWD)
        assert c.post("/api/graduate/cv", files={"file": ("cv.pdf", b"pas un pdf", "application/pdf")}).status_code == 422
        assert c.post("/api/graduate/cv", files={"file": ("cv.exe", b"MZ", "application/octet-stream")}).status_code == 422
        assert c.post("/api/graduate/cv", files={"file": ("cv.pdf", b"%PDF-1.4 test", "application/pdf")}).status_code == 200
        assert c.get("/api/graduate/cv").status_code == 200

    def test_password_change(self):
        c = login("bob@etu.bj", PWD)
        assert c.post("/api/auth/change-password", json={"current_password": "faux", "new_password": "Nouveau123"}).status_code == 403
        assert c.post("/api/auth/change-password", json={"current_password": PWD, "new_password": "Nouveau123"}).status_code == 200
        login("bob@etu.bj", "Nouveau123")


# ------------------------------------------------------------------ parcours entreprise + abonnements
class TestCompany:
    def test_register_pending_cannot_work(self):
        c = new_client()
        r = c.post("/api/auth/register-organization", json={"email": "ent@test.bj", "password": PWD, "full_name": "RH Ent", "role": "company",
                                                             "org_name": "Agro Test SARL", "accept_terms": True})
        assert r.status_code == 201
        assert c.get("/api/company/offers").status_code == 403
        assert c.put("/api/company/org", json={"name": "Agro Test SARL", "sector": "Production végétale", "city": "Cotonou"}).status_code == 200

    def test_admin_validates_company(self, admin):
        oid = next(o["id"] for o in admin.get("/api/admin/orgs?kind=company").json() if o["name"] == "Agro Test SARL")
        S["co"] = oid
        assert admin.post(f"/api/admin/orgs/{oid}/status", json={"status": "validated"}).status_code == 200

    def test_no_subscription_blocks_publishing_and_search(self, admin):
        c = login("ent@test.bj", PWD)
        lv = level_id(c, "TECH")
        body = {"title": "Technicien agricole", "description": "Poste de technicien agricole", "type": "job", "degree_level_id": lv, "status": "published",
                "location": "Abomey-Calavi", "specialty_id": spec_id(c, "Production végétale"), "required_skills": ["Irrigation"], "min_experience_years": 0.5}
        created = c.post("/api/company/offers", json=body)
        assert created.status_code == 201  # même avec l'ancien champ publié, le serveur crée un brouillon
        assert created.json()["status"] == "draft"
        assert c.patch(f"/api/company/offers/{created.json()['id']}", json={"status": "pending_review"}).status_code == 200
        assert admin.post(f"/api/admin/offers/{created.json()['id']}/review", json={"action": "approve"}).status_code == 402
        assert c.get("/api/company/talents").status_code == 402
        assert c.post("/api/company/offers", json={**body, "status": "draft"}).status_code == 201  # brouillon permis
        assert c.post("/api/company/offers", json={k: v for k, v in body.items() if k != "degree_level_id"}).status_code == 422  # diplôme obligatoire

    def test_degree_level_required_and_validated(self):
        c = login("ent@test.bj", PWD)
        r = c.post("/api/company/offers", json={"title": "Poste X", "description": "Description suffisante", "type": "job", "degree_level_id": 99999})
        assert r.status_code == 422

    def test_salary_and_benefits_fields_are_validated_and_saved(self):
        c = login("ent@test.bj", PWD)
        lv = level_id(c, "TECH")
        base = {"title": "Agent de terrain", "description": "Description détaillée du poste", "type": "job", "degree_level_id": lv}
        assert c.post("/api/company/offers", json={**base, "salary_type": "range", "salary_min": 200000, "salary_max": 100000}).status_code == 422
        assert c.post("/api/company/offers", json={**base, "salary_type": "fixed"}).status_code == 422
        r = c.post("/api/company/offers", json={**base, "salary_type": "range", "salary_min": 100000, "salary_max": 180000, "salary_period": "month", "benefits": "Transport et assurance santé"})
        assert r.status_code == 201, r.text
        assert r.json()["salary"]["min"] == 100000 and r.json()["salary"]["max"] == 180000
        assert r.json()["benefits"] == "Transport et assurance santé"

    def test_subscribe_demo_payment_activates(self):
        c = login("ent@test.bj", PWD)
        assert c.get("/api/plans").json()["payment_mode"] == "demo"
        r = c.post("/api/billing/subscribe", json={"plan_code": "starter", "months": 1})
        assert r.status_code == 201, r.text
        ref_ = r.json()["payment"]["reference"]
        assert r.json()["checkout"]["mode"] == "demo" and r.json()["invoice"]["demo"] is True
        assert c.get("/api/billing/overview").json()["entitlements"]["active"] is False  # pas encore payé
        assert c.post(f"/api/billing/payments/{ref_}/confirm-demo").status_code == 200
        ov = c.get("/api/billing/overview").json()
        assert ov["entitlements"]["active"] and ov["entitlements"]["plan"]["code"] == "starter"
        assert ov["invoices"][0]["status"] == "paid" and ov["payments"][0]["status"] == "succeeded"
        assert c.post(f"/api/billing/payments/{ref_}/confirm-demo").status_code == 409

    def test_starter_quota_and_feature_limits(self, admin):
        c = login("ent@test.bj", PWD)
        lv = level_id(c, "TECH")
        body = {"title": "Technicien agricole", "description": "Poste de technicien agricole", "type": "job", "degree_level_id": lv, "status": "published",
                "location": "Abomey-Calavi", "specialty_id": spec_id(c, "Production végétale"), "required_skills": ["Irrigation", "Gestion des sols"]}
        g = login("ama@etu.bj", PWD)
        profile = g.get("/api/graduate/profile").json()
        consent = {k: profile[k] for k in ("headline", "bio", "location", "phone", "availability", "available_from", "visible", "show_contact", "show_cv")}
        consent["matching_opt_in"] = True
        assert g.put("/api/graduate/profile", json=consent).status_code == 200
        ids = []
        for i in range(2):
            r = c.post("/api/company/offers", json={**body, "title": f"Offre {i}"}); assert r.status_code == 201, r.text; ids.append(r.json()["id"])
            assert c.patch(f"/api/company/offers/{ids[-1]}", json={"status": "published"}).status_code == 403  # aucun contournement de la revue
            assert c.patch(f"/api/company/offers/{ids[-1]}", json={"status": "pending_review"}).status_code == 200
            if i == 0:
                returned = admin.post(f"/api/admin/offers/{ids[-1]}/review", json={"action": "request_changes", "reason": "Préciser les missions et le profil attendu"})
                assert returned.status_code == 200 and returned.json()["status"] == "changes_requested"
                assert c.patch(f"/api/company/offers/{ids[-1]}", json={"title": "Offre 0 corrigée", "status": "pending_review"}).status_code == 200
            reviewed = admin.post(f"/api/admin/offers/{ids[-1]}/review", json={"action": "approve"})
            assert reviewed.status_code == 200, reviewed.text
        matches = g.get("/api/graduate/matching").json()
        assert len(matches) == 2 and all(m["score"] > 0 and m["rank"] == 1 and m["total"] == 1 for m in matches)
        # Retirer le consentement efface les snapshots personnels, sans bloquer les candidatures manuelles.
        consent["matching_opt_in"] = False
        assert g.put("/api/graduate/profile", json=consent).status_code == 200
        assert g.get("/api/graduate/matching").json() == []
        available = g.get("/api/graduate/offers").json()["items"]
        assert len(available) == 2 and all(item["my_match"] is None for item in available)
        # Le consentement peut être réactivé ; les candidatures restent une action séparée.
        consent["matching_opt_in"] = True
        assert g.put("/api/graduate/profile", json=consent).status_code == 200
        S["offer"] = ids[0]
        third = c.post("/api/company/offers", json={**body, "title": "Offre 3"})
        assert third.status_code == 201
        assert c.patch(f"/api/company/offers/{third.json()['id']}", json={"status": "pending_review"}).status_code == 200
        assert admin.post(f"/api/admin/offers/{third.json()['id']}/review", json={"action": "approve"}).status_code == 402  # quota Starter = 2
        assert c.get("/api/company/talents").status_code == 403   # recherche non incluse dans Starter
        assert c.get(f"/api/company/offers/{ids[0]}/recommendations").status_code == 403
        assert c.get("/api/company/talents/1").status_code == 403

    def test_public_listing_shows_degree_requirement(self):
        offers = new_client().get("/api/opportunities").json()["items"]
        o = next(x for x in offers if x["id"] == S["offer"])
        assert o["degree"]["level"]["code"] == "TECH" and o["degree"]["mandatory"] is True

    def test_graduate_applies_and_company_processes(self):
        g = login("ama@etu.bj", PWD)
        offers = g.get("/api/graduate/offers").json()["items"]
        mine = next(o for o in offers if o["id"] == S["offer"])
        assert mine["my_match"]["score"] > 0 and mine["my_match"]["criteria"]
        profile = g.get("/api/graduate/profile").json()
        consent = {k: profile[k] for k in ("headline", "bio", "location", "phone", "availability", "available_from", "visible", "show_contact", "show_cv")}
        consent["matching_opt_in"] = False
        assert g.put("/api/graduate/profile", json=consent).status_code == 200
        opted_out = next(o for o in g.get("/api/graduate/offers").json()["items"] if o["id"] == S["offer"])
        assert opted_out["my_match"] is None
        assert g.post(f"/api/graduate/offers/{S['offer']}/apply", json={"cover_letter": "Motivée"}).status_code == 201
        consent["matching_opt_in"] = True
        assert g.put("/api/graduate/profile", json=consent).status_code == 200
        assert g.post(f"/api/graduate/offers/{S['offer']}/apply", json={}).status_code == 409
        c = login("ent@test.bj", PWD)
        apps = c.get(f"/api/company/offers/{S['offer']}/applications").json()
        assert len(apps) == 1 and apps[0]["degrees"][0]["title"].startswith("DEAT") and apps[0]["match"] is None  # Starter : correspondance verrouillée
        aid = apps[0]["id"]
        assert c.patch(f"/api/company/applications/{aid}/status", json={"status": "accepted"}).status_code == 409  # transition interdite
        for st in ("under_review", "shortlisted", "interview", "accepted"):
            assert c.patch(f"/api/company/applications/{aid}/status", json={"status": st}).status_code == 200
        h = g.get("/api/graduate/applications").json()[0]
        assert h["status"] == "accepted" and len(h["history"]) == 5
        assert any("statut" in n["message"] for n in g.get("/api/notifications").json())

    def test_other_company_cannot_touch_offer(self, admin):
        c = new_client()
        c.post("/api/auth/register-organization", json={"email": "ent2@test.bj", "password": PWD, "full_name": "RH Deux", "role": "company", "org_name": "Autre SA", "accept_terms": True})
        oid = next(o["id"] for o in admin.get("/api/admin/orgs?kind=company").json() if o["name"] == "Autre SA")
        admin.post(f"/api/admin/orgs/{oid}/status", json={"status": "validated"})
        assert c.get(f"/api/company/offers/{S['offer']}").status_code == 404
        assert c.get(f"/api/company/offers/{S['offer']}/applications").status_code == 404


# ------------------------------------------------------------------ plan Professional : recherche, matching, quotas de consultation
class TestProfessional:
    def test_upgrade_and_search(self, admin):
        c = login("ent@test.bj", PWD)
        r = c.post("/api/billing/subscribe", json={"plan_code": "professional", "months": 1}).json()
        c.post(f"/api/billing/payments/{r['payment']['reference']}/confirm-demo")
        assert c.get("/api/billing/overview").json()["entitlements"]["plan"]["code"] == "professional"
        g = login("ama@etu.bj", PWD)
        profile = g.get("/api/graduate/profile").json()
        consent = {k: profile[k] for k in ("headline", "bio", "location", "phone", "availability", "available_from", "visible", "show_contact", "show_cv")}
        consent["matching_opt_in"] = False
        assert g.put("/api/graduate/profile", json=consent).status_code == 200
        assert c.get(f"/api/company/talents?offer_id={S['offer']}").json()["total"] == 0
        assert c.get("/api/company/talents").json()["total"] >= 1  # recherche manuelle toujours possible
        consent["matching_opt_in"] = True
        assert g.put("/api/graduate/profile", json=consent).status_code == 200
        res = c.get(f"/api/company/talents?offer_id={S['offer']}").json()
        assert res["total"] >= 1
        t = res["items"][0]
        assert t["degree"]["title"] and t["full_name"] and "match" in t and t["match"]["criteria"]  # l'identité est mise en avant dans le matching
        assert {"degree", "experience", "reputation", "availability"} <= set(t)  # axes séparés
        S["pid"] = t["id"]
        assert c.get("/api/company/talents?level_id=%d" % level_id(c, "MASTER")).json()["total"] == 0  # filtre de diplôme (au moins Master)

    def test_view_profile_counts_quota_once_and_hides_contact(self):
        c = login("ent@test.bj", PWD)
        before = c.get("/api/billing/overview").json()["entitlements"]["views"]["used"]
        d = c.get(f"/api/company/talents/{S['pid']}?offer_id={S['offer']}").json()
        c.get(f"/api/company/talents/{S['pid']}")
        after = c.get("/api/billing/overview").json()["entitlements"]["views"]["used"]
        assert after == before + 1 and d["contact"] is None and d["full_name"]

    def test_company_selects_talent_and_notifies_graduate(self):
        c = login("ent@test.bj", PWD)
        r = c.post("/api/company/selections", json={"offer_id": S["offer"], "graduate_ids": [S["pid"]]})
        assert r.status_code == 201 and r.json()["selected"] == [S["pid"]]
        again = c.post("/api/company/selections", json={"offer_id": S["offer"], "graduate_ids": [S["pid"]]})
        assert again.status_code == 201 and again.json()["already_selected"] == [S["pid"]]
        g = login("ama@etu.bj", PWD)
        assert any("sélectionné" in n["message"] for n in g.get("/api/notifications").json())

    def test_admin_edits_plan_limits_enforced_immediately(self, admin):
        plans = admin.get("/api/admin/plans").json()
        pro = next(p for p in plans if p["code"] == "professional")
        body = {k: pro[k] for k in ("code", "name", "description", "price_xof", "duration_days", "max_active_offers", "can_search", "can_advanced_filters",
                                    "can_see_matching", "can_see_contacts", "active", "sort")}
        assert admin.put(f"/api/admin/plans/{pro['id']}", json={**body, "profile_views_per_month": 1}).status_code == 200
        c = login("ent@test.bj", PWD)
        others = [t for t in c.get("/api/company/talents").json()["items"] if t["id"] != S["pid"]]
        if others:
            assert c.get(f"/api/company/talents/{others[0]['id']}").status_code == 402  # quota atteint
        assert c.get(f"/api/company/talents/{S['pid']}").status_code == 200  # déjà consulté ce mois-ci : gratuit
        admin.put(f"/api/admin/plans/{pro['id']}", json={**body, "profile_views_per_month": 50})

    def test_recommendations_explained_and_unavailable_not_excluded(self):
        c = login("ent@test.bj", PWD)
        r = c.get(f"/api/company/offers/{S['offer']}/recommendations").json()
        assert r["items"] and all(i["match"]["criteria"] for i in r["items"])


# ------------------------------------------------------------------ collaborations, évaluations, réputation, modération
class TestReputation:
    def test_accepted_application_created_verified_collaboration_then_evaluate(self):
        c = login("ent@test.bj", PWD)
        collabs = c.get("/api/company/collaborations").json()
        assert collabs and collabs[0]["status"] == "verified" and collabs[0]["source"] == "platform"
        cid = collabs[0]["id"]
        bad = {"collaboration_id": cid, "technical": 6, "deadlines": 4, "adaptability": 4, "professionalism": 4, "teamwork": 4, "results": 4}
        assert c.post("/api/company/evaluations", json=bad).status_code == 422
        leak = {**bad, "technical": 5, "comment": "Contactez-la au +229 97 00 00 00 ou ama@gmail.com"}
        assert c.post("/api/company/evaluations", json=leak).status_code == 422  # pas de coordonnées dans un commentaire
        ok = {**bad, "technical": 5, "comment": "Très sérieuse."}
        r = c.post("/api/company/evaluations", json=ok)
        assert r.status_code == 201, r.text
        assert c.post("/api/company/evaluations", json=ok).status_code == 409  # une seule évaluation par collaboration
        S["eval"] = r.json()["id"]
        assert c.post("/api/company/recommendations", json={"collaboration_id": cid, "text": "Recommandation détaillée et sincère de son travail."}).status_code == 201

    def test_cannot_evaluate_unverified_collaboration(self):
        c = login("ent@test.bj", PWD)
        r = c.post("/api/company/collaborations", json={"graduate_id": S["pid"], "title": "Mission passée", "start_date": "2024-01-01", "end_date": "2024-02-01"})
        assert r.status_code == 201 and r.json()["status"] == "pending"
        cid = r.json()["id"]
        e = {"collaboration_id": cid, "technical": 3, "deadlines": 3, "adaptability": 3, "professionalism": 3, "teamwork": 3, "results": 3}
        assert c.post("/api/company/evaluations", json=e).status_code == 409
        S["pending_collab"] = cid

    def test_graduate_sees_responds_contests_and_admin_moderates(self, admin):
        g = login("ama@etu.bj", PWD)
        ev = g.get("/api/graduate/evaluations").json()
        assert len(ev["evaluations"]) == 1 and len(ev["recommendations"]) == 1
        assert g.post(f"/api/graduate/evaluations/{S['eval']}/respond", json={"response": "Merci pour ce retour."}).status_code == 200
        rep_before = g.get("/api/graduate/profile").json()["reputation"]
        assert rep_before["evaluations_count"] == 1
        assert g.post(f"/api/graduate/evaluations/{S['eval']}/contest", json={"kind": "evaluation", "target_id": S["eval"], "reason": "Je conteste cette évaluation."}).status_code == 200
        assert g.get("/api/graduate/profile").json()["reputation"]["evaluations_count"] == 0  # retirée du calcul pendant l'examen
        rep = next(r for r in admin.get("/api/admin/reports?status=open").json() if r["kind"] == "evaluation")
        assert admin.post(f"/api/admin/reports/{rep['id']}/resolve", json={"action": "keep"}).status_code == 200
        assert g.get("/api/graduate/profile").json()["reputation"]["evaluations_count"] == 1  # maintenue
        assert admin.post(f"/api/admin/collaborations/{S['pending_collab']}/verify", json={"approve": True}).status_code == 200

    def test_other_graduate_cannot_contest(self):
        b = login("bob@etu.bj", "Nouveau123")
        assert b.post(f"/api/graduate/evaluations/{S['eval']}/contest", json={"kind": "evaluation", "target_id": S["eval"], "reason": "Pas la mienne mais je conteste"}).status_code == 404


# ------------------------------------------------------------------ rôles, suspension, administration
class TestRolesAndAdmin:
    def test_role_isolation(self):
        g, c = login("ama@etu.bj", PWD), login("ent@test.bj", PWD)
        assert g.get("/api/company/offers").status_code == 403
        assert c.get("/api/graduate/profile").status_code == 403
        assert c.get("/api/admin/dashboard").status_code == 403
        assert new_client().get("/api/graduate/profile").status_code == 401

    def test_admin_dashboard_and_taxonomy(self, admin):
        d = admin.get("/api/admin/dashboard").json()
        assert d["users"]["graduate"] >= 2 and "todo" in d
        r = admin.post("/api/admin/levels", json={"code": "CERT", "label": "Certificat spécialisé", "family": "Autre", "rank": 2})
        assert r.status_code == 201
        assert admin.post("/api/admin/levels", json={"code": "CERT", "label": "Doublon", "rank": 2}).status_code == 409
        assert admin.post("/api/admin/specialties", json={"name": "Apiculture", "domain": "Élevage"}).status_code == 201

    def test_admin_updates_matching_weights(self, admin):
        assert admin.put("/api/admin/settings/matching-weights", json={"degree": 50, "specialty": 10, "skills": 20, "experience": 10, "location": 5, "availability": 5}).status_code == 200
        assert admin.get("/api/admin/settings").json()["matching_weights"]["degree"] == 50
        assert admin.put("/api/admin/settings/matching-weights", json={"degree": 0, "specialty": 0, "skills": 0, "experience": 0, "location": 0, "availability": 0}).status_code == 422

    def test_suspended_user_cannot_login_and_session_dies(self, admin):
        uid = next(u["id"] for u in admin.get("/api/admin/users?q=bob@etu.bj").json()["items"])
        b = login("bob@etu.bj", "Nouveau123")
        assert admin.post(f"/api/admin/users/{uid}/status", json={"status": "suspended"}).status_code == 200
        assert b.get("/api/auth/me").status_code == 401
        assert new_client().post("/api/auth/login", json={"email": "bob@etu.bj", "password": "Nouveau123"}).status_code == 403
        assert admin.post(f"/api/admin/users/{uid}/status", json={"status": "active"}).status_code == 200
        login("bob@etu.bj", "Nouveau123")

    def test_suspended_organization_hides_offers(self, admin):
        assert any(o["id"] == S["offer"] for o in new_client().get("/api/opportunities").json()["items"])
        admin.post(f"/api/admin/orgs/{S['co']}/status", json={"status": "suspended", "reason": "Contrôle"})
        assert not any(o["id"] == S["offer"] for o in new_client().get("/api/opportunities").json()["items"])
        assert login("ent@test.bj", PWD).get("/api/company/offers").status_code == 403
        admin.post(f"/api/admin/orgs/{S['co']}/status", json={"status": "validated"})

    def test_offer_moderation(self, admin):
        assert admin.post(f"/api/admin/offers/{S['offer']}/moderation", json={"moderation": "suspended", "reason": "Test"}).status_code == 200
        assert not any(o["id"] == S["offer"] for o in new_client().get("/api/opportunities").json()["items"])
        admin.post(f"/api/admin/offers/{S['offer']}/moderation", json={"moderation": "ok"})

    def test_manual_payment_reconciliation_blocked_in_demo_confirm_but_admin_can_grant(self, admin):
        r = admin.post("/api/admin/subscriptions/grant", json={"org_id": S["co"], "plan_code": "business", "months": 1, "reason": "geste commercial"})
        assert r.status_code == 201 and r.json()["status"] == "active"

    def test_reissue_invitation_only_for_pending(self, admin):
        u = next(x for x in admin.get("/api/admin/users?q=ama@etu.bj").json()["items"])
        assert admin.post(f"/api/admin/users/{u['id']}/invitation").status_code == 404  # déjà actif
        r = admin.post("/api/admin/graduates", json={"full_name": "Manuel Test", "email": "manuel@etu.bj", "degree_title": "DEAT test", "level_id": 1})
        assert r.status_code == 201 and "token=" in r.json()["link"]
        uid = r.json()["user"]["id"]
        assert admin.post(f"/api/admin/users/{uid}/invitation").status_code == 200
