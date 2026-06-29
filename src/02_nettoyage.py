"""02_nettoyage.py — Nettoyage et normalisation des offres brutes.

Livrable II (Stratégie de nettoyage, 3 pts).

Lit les JSON bruts de data/raw/ (immuables), produit :
  - data/processed/offres_clean.csv      : 1 ligne par offre dédoublonnée
  - data/processed/competences_long.csv  : format long (id, competence) pour
                                           les comptages de l'étape 3.

Choix de nettoyage documentés (voir aussi le dossier) :
  * Dédoublonnage par `id` (offres remontées par plusieurs mots-clés).
  * Département dérivé de `lieuTravail.libelle` (préfixe « NN - VILLE »).
  * Salaire : parsing du texte libre `salaire.libelle` (présent ~26 % du temps)
    et normalisation en base ANNUELLE, avec hypothèses explicites.
  * Compétences : le champ structuré `competences[]` n'est rempli que sur ~17 %
    des offres → on DÉTECTE en plus les technologies via un lexique curé appliqué
    au texte (intitulé + description + libellés de compétences). Choix assumé pour
    obtenir une couverture exploitable de la question « compétences demandées ».

Ré-exécutable : `python src/02_nettoyage.py`
"""

from __future__ import annotations

import glob
import io
import json
import re
import sys
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_RAW = RACINE / "data" / "raw"
DOSSIER_PROCESSED = RACINE / "data" / "processed"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Hypothèses de normalisation salariale (documentées) :
# - un temps plein ~ 35h/semaine x 52 semaines = 1820 h/an ;
# - un salaire mensuel est versé sur `sur N mois` (12 par défaut).
HEURES_AN_TEMPS_PLEIN = 35 * 52
MOIS_PAR_AN_DEFAUT = 12


# --- Lexique de compétences Data --------------------------------------------
# Clé = compétence canonique ; valeur = motif regex (recherché en IGNORECASE).
# Les motifs courts/ambigus (R, C, BI) sont volontairement encadrés pour limiter
# les faux positifs.
LEXIQUE_COMPETENCES: dict[str, str] = {
    # Langages
    "Python": r"\bpython\b",
    "R": r"(?<![\w+])R(?:\s*(?:language|studio))?\b(?=\s|,|\.|/|\)|$)",
    "SQL": r"\bsql\b",
    "Java": r"\bjava\b(?!script)",
    "Scala": r"\bscala\b",
    "C++": r"c\+\+",
    "C#": r"c#",
    "JavaScript": r"\bjavascript\b",
    "SAS": r"\bsas\b",
    "Matlab": r"\bmatlab\b",
    "Bash/Shell": r"\b(bash|shell\s*script)\b",
    # Bases de données
    "PostgreSQL": r"\b(postgresql|postgres)\b",
    "MySQL": r"\bmysql\b",
    "Oracle": r"\boracle\b",
    "SQL Server": r"\bsql\s*server\b",
    "MongoDB": r"\bmongo\s*db\b",
    "NoSQL": r"\bnosql\b",
    "Redis": r"\bredis\b",
    "Elasticsearch": r"\b(elasticsearch|elastic\s*search)\b",
    # Big Data / traitement
    "Spark": r"\b(spark|pyspark)\b",
    "Hadoop": r"\bhadoop\b",
    "Hive": r"\bhive\b",
    "Kafka": r"\bkafka\b",
    "Airflow": r"\bairflow\b",
    "dbt": r"\bdbt\b",
    "ETL": r"\betl\b",
    "Databricks": r"\bdatabricks\b",
    "Talend": r"\btalend\b",
    # Cloud
    "AWS": r"\b(aws|amazon\s*web\s*services)\b",
    "Azure": r"\bazure\b",
    "GCP": r"\b(gcp|google\s*cloud)\b",
    "Snowflake": r"\bsnowflake\b",
    "BigQuery": r"\bbig\s*query\b",
    "Redshift": r"\bredshift\b",
    # BI / Visualisation
    "Power BI": r"\bpower\s*bi\b",
    "Tableau": r"\btableau\b",
    "Qlik": r"\bqlik(view|\s*sense)?\b",
    "Looker": r"\blooker\b",
    "Excel": r"\bexcel\b",
    "DAX": r"\bdax\b",
    "SSIS/SSAS/SSRS": r"\bss(is|as|rs)\b",
    # Data science / ML
    "Machine Learning": r"\bmachine\s*learning\b",
    "Deep Learning": r"\bdeep\s*learning\b",
    "NLP": r"\b(nlp|traitement.{0,15}langage)\b",
    "TensorFlow": r"\btensorflow\b",
    "PyTorch": r"\bpytorch\b",
    "scikit-learn": r"\b(scikit[- ]?learn|sklearn)\b",
    "Pandas": r"\bpandas\b",
    "NumPy": r"\bnumpy\b",
    # Outils / méthodes
    "Docker": r"\bdocker\b",
    "Kubernetes": r"\b(kubernetes|k8s)\b",
    "Git": r"\bgit(hub|lab)?\b",
    "Linux": r"\blinux\b",
    "Power Query": r"\bpower\s*query\b",
    "Data Visualization": r"\b(data\s*viz|dataviz|data\s*visuali)",
}
_LEXIQUE_COMPILE = {nom: re.compile(motif, re.IGNORECASE)
                    for nom, motif in LEXIQUE_COMPETENCES.items()}


# --- Chargement --------------------------------------------------------------

def charger_offres_brutes() -> list[dict]:
    """Concatène les `resultats` de tous les JSON bruts de data/raw/."""
    fichiers = sorted(glob.glob(str(DOSSIER_RAW / "*.json")))
    if not fichiers:
        raise RuntimeError(
            f"Aucun JSON dans {DOSSIER_RAW}. Lancer d'abord src/01_collecte.py.")
    offres: list[dict] = []
    for chemin in fichiers:
        with io.open(chemin, encoding="utf-8") as f:
            offres.extend(json.load(f).get("resultats", []))
    return offres


# --- Parsing salaire ---------------------------------------------------------

_RE_SALAIRE = re.compile(
    r"(?P<periode>Annuel|Mensuel|Horaire|Cachet)\s+de\s+"
    r"(?P<min>[\d.]+)\s*Euros"
    r"(?:\s*(?:à|a)\s*(?P<max>[\d.]+)\s*Euros)?"
    r"(?:\s*sur\s*(?P<mois>[\d.]+)\s*mois)?",
    re.IGNORECASE,
)


def parser_salaire(libelle: str | None) -> dict:
    """Extrait période, min, max d'un libellé salaire et normalise en annuel.

    Renvoie un dict avec sal_periode, sal_min, sal_max (valeurs brutes dans
    l'unité de la période) et sal_annuel_min / sal_annuel_max / sal_annuel_moyen.
    Toutes les clés valent None si rien n'est exploitable.
    """
    vide = {"sal_periode": None, "sal_min": None, "sal_max": None,
            "sal_annuel_min": None, "sal_annuel_max": None,
            "sal_annuel_moyen": None}
    if not libelle:
        return vide
    m = _RE_SALAIRE.search(libelle)
    if not m:
        return vide

    periode = m.group("periode").capitalize()
    val_min = float(m.group("min"))
    val_max = float(m.group("max")) if m.group("max") else val_min
    mois = float(m.group("mois")) if m.group("mois") else MOIS_PAR_AN_DEFAUT

    # Facteur de passage vers une base annuelle selon la période.
    if periode == "Annuel":
        facteur = 1.0
    elif periode == "Mensuel":
        facteur = mois  # salaire mensuel x nombre de versements/an
    elif periode == "Horaire":
        facteur = HEURES_AN_TEMPS_PLEIN  # hypothèse temps plein 1820 h/an
    else:  # Cachet ou autre : non normalisable de façon fiable
        facteur = None

    an_min = round(val_min * facteur) if facteur else None
    an_max = round(val_max * facteur) if facteur else None
    an_moy = round((an_min + an_max) / 2) if an_min and an_max else an_min

    return {"sal_periode": periode, "sal_min": val_min, "sal_max": val_max,
            "sal_annuel_min": an_min, "sal_annuel_max": an_max,
            "sal_annuel_moyen": an_moy}


# --- Détection de compétences ------------------------------------------------

def detecter_competences(*textes: str | None) -> list[str]:
    """Retourne la liste des compétences du lexique présentes dans les textes."""
    texte = " ".join(t for t in textes if t)
    return [nom for nom, motif in _LEXIQUE_COMPILE.items() if motif.search(texte)]


# --- Extraction d'une offre --------------------------------------------------

def _departement(lieu: dict | None) -> str | None:
    """Déduit le département du préfixe « NN - VILLE » de lieuTravail.libelle."""
    libelle = (lieu or {}).get("libelle") or ""
    m = re.match(r"\s*(\d{2,3})\s*-", libelle)
    return m.group(1) if m else None


def extraire_offre(o: dict) -> dict:
    """Aplati une offre brute en un enregistrement propre."""
    lieu = o.get("lieuTravail") or {}
    entreprise = o.get("entreprise") or {}
    salaire = o.get("salaire") or {}
    comp_structurees = [c.get("libelle") for c in (o.get("competences") or [])
                        if c.get("libelle")]

    detectees = detecter_competences(
        o.get("intitule"), o.get("description"), " ".join(comp_structurees))

    enreg = {
        "id": o.get("id"),
        "intitule": o.get("intitule"),
        "dateCreation": o.get("dateCreation"),
        "departement": _departement(lieu),
        "commune": lieu.get("commune"),
        "ville": lieu.get("libelle"),
        "latitude": lieu.get("latitude"),
        "longitude": lieu.get("longitude"),
        "entreprise": entreprise.get("nom"),
        "typeContrat": o.get("typeContrat"),
        "typeContratLibelle": o.get("typeContratLibelle"),
        "experienceLibelle": o.get("experienceLibelle"),
        "experienceExige": o.get("experienceExige"),
        "qualificationLibelle": o.get("qualificationLibelle"),
        "romeCode": o.get("romeCode"),
        "romeLibelle": o.get("romeLibelle"),
        "secteurActiviteLibelle": o.get("secteurActiviteLibelle"),
        "salaire_libelle": salaire.get("libelle"),
        "competences_structurees": " | ".join(comp_structurees) or None,
        "competences_detectees": " | ".join(detectees) or None,
        "nb_competences_detectees": len(detectees),
    }
    enreg.update(parser_salaire(salaire.get("libelle")))
    return enreg


# --- Orchestration -----------------------------------------------------------

def main() -> None:
    DOSSIER_PROCESSED.mkdir(parents=True, exist_ok=True)

    brutes = charger_offres_brutes()
    print(f"Offres brutes chargées      : {len(brutes)}")

    df = pd.DataFrame(extraire_offre(o) for o in brutes)
    avant = len(df)
    df = df.drop_duplicates(subset="id").reset_index(drop=True)
    print(f"Après dédoublonnage par id  : {len(df)} (-{avant - len(df)} doublons)")

    # Typage des dates.
    df["dateCreation"] = pd.to_datetime(df["dateCreation"], errors="coerce",
                                        utc=True)

    # --- Rapport qualité (à citer dans le dossier) ---------------------------
    n = len(df)
    taux_sal = df["sal_annuel_moyen"].notna().mean()
    taux_comp_struct = df["competences_structurees"].notna().mean()
    taux_comp_detect = (df["nb_competences_detectees"] > 0).mean()
    print("\n--- Qualité des données ---")
    print(f"Salaire annuel exploitable  : {taux_sal:.0%} des offres")
    print(f"Compétences (champ structuré): {taux_comp_struct:.0%} des offres")
    print(f"Compétences (détection texte): {taux_comp_detect:.0%} des offres")
    print(f"Départements distincts      : {df['departement'].nunique()}")

    # --- Écriture table principale ------------------------------------------
    chemin_offres = DOSSIER_PROCESSED / "offres_clean.csv"
    df.to_csv(chemin_offres, index=False, encoding="utf-8")
    print(f"\nÉcrit : {chemin_offres.relative_to(RACINE)} ({n} lignes)")

    # --- Écriture table compétences en format long --------------------------
    lignes = [
        {"id": row.id, "competence": comp}
        for row in df.itertuples()
        if row.competences_detectees
        for comp in row.competences_detectees.split(" | ")
    ]
    df_comp = pd.DataFrame(lignes)
    chemin_comp = DOSSIER_PROCESSED / "competences_long.csv"
    df_comp.to_csv(chemin_comp, index=False, encoding="utf-8")
    print(f"Écrit : {chemin_comp.relative_to(RACINE)} "
          f"({len(df_comp)} couples offre-compétence)")


if __name__ == "__main__":
    main()
