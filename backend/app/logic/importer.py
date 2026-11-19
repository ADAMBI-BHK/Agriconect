"""Lecture et contrôle des fichiers de listes transmis par les établissements (CSV ou Excel). Fonctions pures."""
from __future__ import annotations
import csv, io, re
from dataclasses import dataclass, field
from datetime import date
from .text import norm

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
COLUMNS = ["nom_complet", "email", "telephone", "diplome", "niveau", "specialite", "annee_obtention", "mention", "pays"]
ALIASES = {
    "nom_complet": {"nom_complet", "nom", "nom_et_prenoms", "nom_prenoms", "full_name", "name", "candidat"},
    "email": {"email", "e_mail", "courriel", "mail"},
    "telephone": {"telephone", "tel", "phone", "contact"},
    "diplome": {"diplome", "intitule", "intitule_diplome", "intitule_du_diplome", "degree", "titre"},
    "niveau": {"niveau", "niveau_diplome", "cycle", "level"},
    "specialite": {"specialite", "filiere", "option", "domaine", "specialty"},
    "annee_obtention": {"annee_obtention", "annee", "annee_diplome", "year", "annee_d_obtention"},
    "mention": {"mention", "resultat", "honors"},
    "pays": {"pays", "country"},
}
TEMPLATE_CSV = ("nom_complet;email;telephone;diplome;niveau;specialite;annee_obtention;mention;pays\n"
                "Akouavi Dossou;akouavi.dossou@exemple.bj;+22997000000;Licence professionnelle en production végétale;"
                "Licence professionnelle;Production végétale;2025;Bien;Bénin\n")


class ImportError_(Exception):
    pass


@dataclass
class ParsedRow:
    line_no: int
    data: dict
    errors: list[str] = field(default_factory=list)


def _key(h) -> str:
    return re.sub(r"[^a-z0-9]+", "_", norm(str(h or ""))).strip("_")


def _read_table(filename: str, content: bytes) -> list[list]:
    name = (filename or "").lower()
    if name.endswith(".csv") or name.endswith(".txt"):
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
        first = text.splitlines()[0] if text.strip() else ""
        delim = ";" if first.count(";") >= first.count(",") and ";" in first else ","
        return [r for r in csv.reader(io.StringIO(text), delimiter=delim)]
    if name.endswith(".xlsx") or name.endswith(".xlsm"):
        from openpyxl import load_workbook  # import tardif : dépendance facultative pour le reste du module
        try:
            wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        except Exception as e:  # fichier corrompu ou non xlsx
            raise ImportError_("Fichier Excel illisible : enregistrez-le au format .xlsx ou .csv") from e
        ws = wb.active
        return [["" if c is None else c for c in row] for row in ws.iter_rows(values_only=True)]
    raise ImportError_("Format non pris en charge : utilisez un fichier .csv ou .xlsx")


def parse_rows(filename: str, content: bytes, level_lookup: dict[str, str], max_rows: int = 1000,
               today: date | None = None) -> list[ParsedRow]:
    """level_lookup : libellés et codes normalisés (norm) → code de niveau du référentiel."""
    today = today or date.today()
    table = _read_table(filename, content)
    table = [r for r in table if any(str(c).strip() for c in r)]
    if not table:
        raise ImportError_("Le fichier est vide")
    head = [_key(h) for h in table[0]]
    index: dict[str, int] = {}
    for col, aliases in ALIASES.items():
        for i, h in enumerate(head):
            if h in aliases and col not in index:
                index[col] = i
    missing = [c for c in ("nom_complet", "email", "diplome", "niveau") if c not in index]
    if missing:
        raise ImportError_("Colonnes obligatoires absentes : " + ", ".join(missing) + ". Utilisez le modèle fourni.")
    body = table[1:]
    if not body:
        raise ImportError_("Le fichier ne contient aucune ligne de données")
    if len(body) > max_rows:
        raise ImportError_(f"Trop de lignes ({len(body)}) : maximum {max_rows} par liste")
    out, seen = [], set()
    for n, raw in enumerate(body, start=2):
        def cell(col):
            i = index.get(col)
            return str(raw[i]).strip() if i is not None and i < len(raw) and raw[i] is not None else ""
        d = {c: cell(c) for c in COLUMNS}
        errs: list[str] = []
        if len(d["nom_complet"]) < 2:
            errs.append("Nom complet manquant")
        d["email"] = d["email"].lower()
        if not EMAIL.match(d["email"]):
            errs.append("Email invalide")
        elif d["email"] in seen:
            errs.append("Email en double dans le fichier")
        seen.add(d["email"])
        if not d["diplome"]:
            errs.append("Intitulé exact du diplôme manquant")
        code = level_lookup.get(norm(d["niveau"]))
        if not code:
            errs.append(f"Niveau inconnu « {d['niveau']} » (voir les niveaux du référentiel)")
        d["level_code"] = code or ""
        year = None
        if d["annee_obtention"]:
            try:
                year = int(float(d["annee_obtention"]))
                if not 1970 <= year <= today.year + 1:
                    errs.append("Année d'obtention improbable")
            except ValueError:
                errs.append("Année d'obtention invalide")
        d["year"] = year
        d["pays"] = d["pays"] or "Bénin"
        out.append(ParsedRow(n, d, errs))
    return out
