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
```

Chaque script est ré-exécutable de bout en bout sans intervention manuelle.
