"""03_calculs.py — Calcul des KPI et agrégats pour l'analyse.

Livrable III (Calcul, 2 pts). Prépare les tables qui alimentent le notebook
d'analyse (livrable IV).

Entrées (data/processed/) :
  - offres_clean.csv      : 1 ligne par offre
  - competences_long.csv  : couples (id, competence)

Sorties (data/processed/) :
  - kpi_global.csv            : indicateurs synthétiques (1 ligne)
  - top_competences.csv       : compétences les plus demandées (volume + part)
  - competences_salaire.csv    : valorisation salariale par compétence (cœur IV)
  - repartition_departement.csv, repartition_contrat.csv,
    repartition_experience.csv, repartition_metier.csv

Ré-exécutable : `python src/03_calculs.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_PROCESSED = RACINE / "data" / "processed"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Effectif minimum pour qu'une médiane salariale par compétence soit jugée
# fiable (sinon trop de bruit sur de faibles effectifs).
SEUIL_EFFECTIF_SALAIRE = 5


def charger() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Charge les tables nettoyées produites par l'étape 2."""
    offres = DOSSIER_PROCESSED / "offres_clean.csv"
    comp = DOSSIER_PROCESSED / "competences_long.csv"
    if not offres.exists() or not comp.exists():
        raise RuntimeError("Fichiers nettoyés absents. Lancer src/02_nettoyage.py.")
    return pd.read_csv(offres), pd.read_csv(comp)


def kpi_global(df: pd.DataFrame, comp: pd.DataFrame) -> pd.DataFrame:
    """Indicateurs synthétiques sur l'ensemble du corpus."""
    sal = df["sal_annuel_moyen"].dropna()
    kpi = {
        "nb_offres": len(df),
        "nb_departements": df["departement"].nunique(),
        "nb_entreprises": df["entreprise"].nunique(),
        "nb_competences_distinctes": comp["competence"].nunique(),
        "taux_salaire_renseigne": round(df["sal_annuel_moyen"].notna().mean(), 3),
        "salaire_annuel_median": round(sal.median()) if len(sal) else None,
        "salaire_annuel_q1": round(sal.quantile(0.25)) if len(sal) else None,
        "salaire_annuel_q3": round(sal.quantile(0.75)) if len(sal) else None,
    }
    return pd.DataFrame([kpi])


def top_competences(comp: pd.DataFrame, nb_offres: int) -> pd.DataFrame:
    """Compétences les plus demandées : volume et part des offres."""
    t = (comp["competence"].value_counts()
         .rename_axis("competence").reset_index(name="nb_offres"))
    t["part_offres"] = (t["nb_offres"] / nb_offres).round(3)
    return t


def competences_salaire(df: pd.DataFrame, comp: pd.DataFrame) -> pd.DataFrame:
    """Valorisation salariale par compétence (cœur du livrable IV).

    Joint chaque couple (offre, compétence) au salaire annuel de l'offre, puis
    agrège par compétence. Ne conserve que les compétences dont l'effectif
    salarié dépasse le seuil de fiabilité.
    """
    base = comp.merge(df[["id", "sal_annuel_moyen"]], on="id", how="left")
    base = base.dropna(subset=["sal_annuel_moyen"])
    agg = (base.groupby("competence")["sal_annuel_moyen"]
           .agg(nb_offres_salaire="count", salaire_median="median",
                salaire_q1=lambda s: s.quantile(0.25),
                salaire_q3=lambda s: s.quantile(0.75))
           .reset_index())
    agg = agg[agg["nb_offres_salaire"] >= SEUIL_EFFECTIF_SALAIRE]
    for c in ["salaire_median", "salaire_q1", "salaire_q3"]:
        agg[c] = agg[c].round()
    return agg.sort_values("salaire_median", ascending=False).reset_index(drop=True)


def repartition(df: pd.DataFrame, colonne: str) -> pd.DataFrame:
    """Comptage simple des offres par modalité d'une colonne."""
    return (df[colonne].value_counts(dropna=False)
            .rename_axis(colonne).reset_index(name="nb_offres"))


def main() -> None:
    df, comp = charger()
    n = len(df)

    sorties = {
        "kpi_global.csv": kpi_global(df, comp),
        "top_competences.csv": top_competences(comp, n),
        "competences_salaire.csv": competences_salaire(df, comp),
        "repartition_departement.csv": repartition(df, "departement"),
        "repartition_contrat.csv": repartition(df, "typeContratLibelle"),
        "repartition_experience.csv": repartition(df, "experienceLibelle"),
        "repartition_metier.csv": repartition(df, "romeLibelle"),
    }
    for nom, table in sorties.items():
        table.to_csv(DOSSIER_PROCESSED / nom, index=False, encoding="utf-8")

    # --- Aperçu console (cohérence + lien avec la question d'analyse) ---------
    print(f"Corpus : {n} offres\n")
    print("TOP 10 compétences demandées :")
    print(sorties["top_competences.csv"].head(10).to_string(index=False))
    print("\nTOP 10 compétences les mieux valorisées "
          f"(effectif >= {SEUIL_EFFECTIF_SALAIRE}) :")
    print(sorties["competences_salaire.csv"].head(10).to_string(index=False))
    print(f"\n{len(sorties)} tables d'agrégats écrites dans data/processed/.")


if __name__ == "__main__":
    main()
