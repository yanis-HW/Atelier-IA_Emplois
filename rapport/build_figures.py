"""build_figures.py — Génère les figures PNG du dossier LaTeX.

Lit les agrégats de data/processed/ et écrit les figures dans rapport/figures/.
Lancer : `python rapport/build_figures.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # rendu fichier, sans interface
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

RACINE = Path(__file__).resolve().parent.parent
P = RACINE / "data" / "processed"
FIG = Path(__file__).resolve().parent / "figures"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sns.set_theme(style="whitegrid")
FIG.mkdir(parents=True, exist_ok=True)


def fig_demande() -> None:
    """Top 15 des compétences les plus demandées."""
    top = pd.read_csv(P / "top_competences.csv").head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 5.5))
    sns.barplot(data=top, y="competence", x="nb_offres", palette="viridis",
                hue="competence", legend=False, ax=ax)
    for i, (n, pa) in enumerate(zip(top["nb_offres"], top["part_offres"])):
        ax.text(n + 0.8, i, f"{pa:.0%}", va="center", fontsize=8)
    ax.set_title("Top 15 des compétences Data demandées en Île-de-France")
    ax.set_xlabel("Nombre d'offres"); ax.set_ylabel("")
    fig.tight_layout(); fig.savefig(FIG / "fig-demande.png", dpi=150)
    plt.close(fig)


def fig_salaire() -> None:
    """Valorisation salariale médiane par compétence (effectif >= 5)."""
    cs = pd.read_csv(P / "competences_salaire.csv")
    cs = cs.sort_values("salaire_median").tail(15)
    err = [cs["salaire_median"] - cs["salaire_q1"],
           cs["salaire_q3"] - cs["salaire_median"]]
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.barh(cs["competence"], cs["salaire_median"],
            color=sns.color_palette("magma", len(cs)),
            xerr=err, error_kw=dict(ecolor="gray", alpha=0.6, capsize=3))
    ax.set_title("Salaire annuel médian par compétence (effectif ≥ 5)")
    ax.set_xlabel("Salaire annuel médian (€)"); ax.set_ylabel("")
    fig.tight_layout(); fig.savefig(FIG / "fig-salaire.png", dpi=150)
    plt.close(fig)


def fig_scatter() -> None:
    """Croisement demande (volume) vs valorisation (salaire médian)."""
    top = pd.read_csv(P / "top_competences.csv")
    cs = pd.read_csv(P / "competences_salaire.csv")
    m = top.merge(cs, on="competence")
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    ax.scatter(m["nb_offres"], m["salaire_median"], s=70, color="#C44E52",
               alpha=0.8)
    for _, r in m.iterrows():
        ax.annotate(r["competence"], (r["nb_offres"], r["salaire_median"]),
                    xytext=(4, 4), textcoords="offset points", fontsize=8)
    ax.axhline(m["salaire_median"].median(), color="gray", ls=":", alpha=0.7)
    ax.axvline(m["nb_offres"].median(), color="gray", ls=":", alpha=0.7)
    ax.set_title("Compétences Data : demande vs valorisation salariale")
    ax.set_xlabel("Nombre d'offres (demande)")
    ax.set_ylabel("Salaire annuel médian (€)")
    fig.tight_layout(); fig.savefig(FIG / "fig-scatter.png", dpi=150)
    plt.close(fig)


def fig_panorama() -> None:
    """Répartitions par département, contrat et expérience."""
    dep = pd.read_csv(P / "repartition_departement.csv").dropna(
        subset=["departement"]).copy()
    dep["departement"] = dep["departement"].astype(int).astype(str)
    dep = dep.sort_values("nb_offres", ascending=False)
    contrat = pd.read_csv(P / "repartition_contrat.csv").dropna().sort_values(
        "nb_offres", ascending=False).head(5)
    exp = pd.read_csv(P / "repartition_experience.csv").dropna().sort_values(
        "nb_offres", ascending=False).head(6)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    sns.barplot(data=dep, x="departement", y="nb_offres", ax=axes[0],
                palette="Blues_r", hue="departement", legend=False)
    axes[0].set_title("Offres par département"); axes[0].set_xlabel("Département")
    axes[0].set_ylabel("Nombre d'offres")
    sns.barplot(data=contrat, y="typeContratLibelle", x="nb_offres", ax=axes[1],
                palette="Greens_r", hue="typeContratLibelle", legend=False)
    axes[1].set_title("Types de contrat (top 5)"); axes[1].set_xlabel("")
    axes[1].set_ylabel("")
    sns.barplot(data=exp, y="experienceLibelle", x="nb_offres", ax=axes[2],
                palette="Oranges_r", hue="experienceLibelle", legend=False)
    axes[2].set_title("Expérience demandée (top 6)"); axes[2].set_xlabel("")
    axes[2].set_ylabel("")
    fig.tight_layout(); fig.savefig(FIG / "fig-panorama.png", dpi=150)
    plt.close(fig)


def main() -> None:
    fig_panorama()
    fig_demande()
    fig_salaire()
    fig_scatter()
    print(f"Figures écrites dans {FIG.relative_to(RACINE)}/ :")
    for f in sorted(FIG.glob("*.png")):
        print("  -", f.name)


if __name__ == "__main__":
    main()
