import re, unicodedata


def norm(s: str) -> str:
    """Minuscules, sans accents, espaces normalisés : sert aux comparaisons de compétences, intitulés, etc."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", s).strip()


def csv_list(s: str) -> list[str]:
    return [x.strip() for x in (s or "").replace("\n", ",").replace(";", ",").split(",") if x.strip()]
