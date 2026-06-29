# Analyse du marché de l'emploi Data en Île-de-France

Projet d'atelier IA (M1 MIAGE, Paris 1) — analyse du marché de l'emploi IT/Data
en **Île-de-France** à partir de données collectées automatiquement via l'**API
REST officielle France Travail** (ex-Pôle Emploi).

> **Question fil rouge :** *Quelles compétences Data sont les plus demandées en
> Île-de-France et comment se valorisent-elles salarialement ?*

## Pourquoi l'API (et pas du scraping) ?

Parmi les techniques de collecte (BeautifulSoup, Selenium/Playwright, API REST),
l'API REST a été retenue car elle domine sur :
- **la légalité** : licence de réutilisation officielle (vs CGU des job boards) ;
- **la robustesse** : JSON structuré et versionné (vs HTML fragile) ;
- **la pertinence** : aucune page à rendre, donc pas de navigateur headless.

Principe appliqué : **API si disponible > parsing HTML > navigateur headless**.

## Pour l'évaluateur — exécuter le projet

Le code est entièrement ré-exécutable. Comme les identifiants API ne sont **pas**
versionnés (bonne pratique de sécurité), il faut fournir les vôtres :

1. **Créer une application** sur [francetravail.io](https://francetravail.io)
   (espace développeur) et **souscrire à l'API « Offres d'emploi v2 »** pour
   obtenir un `client_id` et un `client_secret`.
2. **Configurer les secrets** : `cp .env.example .env` puis renseigner les 4 clés.
   Les valeurs `FT_TOKEN_URL` et `FT_SCOPE` sont déjà documentées dans
   `.env.example` (endpoint OAuth2 et scopes `api_offresdemploiv2 o2dsoffre`).
3. **Installer et lancer** (voir [Installation](#installation) et
   [Pipeline](#pipeline-à-exécuter-dans-lordre) ci-dessous).

> Sans relancer la collecte (étape 01), les données nettoyées et les agrégats sont
> **déjà versionnés** dans `data/processed/` : le notebook d'analyse
> (`notebooks/04_analyse.ipynb`) et le dossier sont donc consultables et
> ré-exécutables **sans clé API**. La clé n'est nécessaire que pour recollecter
> des offres fraîches via `src/01_collecte.py`.

## Structure du dépôt

```
.
├── data/
│   ├── raw/             # JSON bruts de l'API (NON versionnés, immuables)
│   └── processed/       # CSV nettoyés / agrégats
├── src/
│   ├── 01_collecte.py   # auth OAuth2 + recherche paginée -> data/raw/
│   ├── 02_nettoyage.py  # data/raw -> data/processed
│   └── 03_calculs.py    # KPI et agrégats
├── notebooks/
│   └── 04_analyse.ipynb # visualisations + interprétation
└── rapport/             # dossier final
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # puis remplir les identifiants France Travail
```

Créer une application sur [francetravail.io](https://francetravail.io) pour obtenir
`FT_CLIENT_ID` / `FT_CLIENT_SECRET`, et renseigner `FT_TOKEN_URL` / `FT_SCOPE`.

## Pipeline (à exécuter dans l'ordre)

```bash
python src/01_collecte.py     # -> data/raw/      (offres IDF)
python src/02_nettoyage.py    # -> data/processed/offres_clean.csv
python src/03_calculs.py      # -> agrégats KPI
jupyter notebook notebooks/04_analyse.ipynb
python rapport/build_pdf.py   # -> rapport/rapport.pdf (dossier final)
```

Chaque script est ré-exécutable de bout en bout sans intervention manuelle.

## Livrables

| Livrable | Fichier |
|---|---|
| I — Plan de récolte | `src/01_collecte.py` + `rapport/rapport.tex` §2 |
| II — Nettoyage | `src/02_nettoyage.py` + `rapport/rapport.tex` §3 |
| III — Calcul | `src/03_calculs.py` + `rapport/rapport.tex` §4 |
| IV — Analyse | `notebooks/04_analyse.ipynb` + `rapport/rapport.tex` §5 |
| V — Conclusion | `rapport/rapport.tex` §6 |

### Dossier final

Le dossier rédigé est `rapport/rapport.tex` (LaTeX, version formelle attendue).
Pour le compiler en PDF :

```bash
python rapport/build_figures.py          # (re)génère les figures dans rapport/figures/
cd rapport && pdflatex rapport.tex && pdflatex rapport.tex   # 2 passes (table des matières)
```

À défaut de LaTeX installé localement, déposer `rapport.tex` et le dossier
`figures/` sur [Overleaf](https://www.overleaf.com) (compilation pdfLaTeX).

Une version Markdown allégée du dossier est aussi disponible
(`rapport/rapport.md`, convertible via `python rapport/build_pdf.py`).
