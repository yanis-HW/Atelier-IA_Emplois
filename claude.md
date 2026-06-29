# CLAUDE.md

Contexte projet pour Claude Code. Lis ce fichier avant toute action.

## 1. Contexte & objectif

Projet d'atelier IA (M1 MIAGE, Paris 1) en **binôme**, noté sur 20.
Sujet : **analyse du marché de l'emploi IT/Data en France** à partir de données
collectées automatiquement.

Restitution : **dépôt Git** + dossier rédigé + **fichiers ré-exécutables**.
Une forme professionnelle, claire et structurée est attendue, et chaque choix
technique doit être **justifié par écrit** dans le dossier.

## 2. Barème (à garder en tête pour prioriser le travail)

| Livrable | Points | Fichier responsable |
|---|---|---|
| I — Plan de récolte de données | 5 | `src/01_collecte.py` + section dossier |
| II — Stratégie de nettoyage | 3 | `src/02_nettoyage.py` + section dossier |
| III — Calcul | 2 | `src/03_calculs.py` |
| IV — Analyse | 5 | `notebooks/04_analyse.ipynb` |
| V — Conclusion | 3 | section dossier |
| Forme professionnelle + Git | 2 | README, structure, commits |

## 3. Source de données — API Offres d'emploi France Travail

Décision : on utilise l'**API REST officielle** de France Travail (ex-Pôle Emploi).
NE PAS scraper de job board (Indeed, LinkedIn, Welcome to the Jungle) : c'est
contraire à leurs CGU et fragile.

**Justification retenue** (parmi les techniques vues en cours : BeautifulSoup,
Selenium/Playwright, API REST) : l'API domine sur la légalité (licence de
réutilisation), la robustesse (JSON structuré et versionné) et la pertinence
(pas besoin de navigateur headless puisqu'aucun rendu JS à charger). Principe :
**API si disponible > parsing HTML > navigateur headless**. Selenium aurait été
le repli si aucune API n'existait.

Détails techniques :
- Auth : OAuth2 **client_credentials grant** (pas d'auth utilisateur final).
- Base de recherche : `https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search`
- Pagination : paramètre `range` (`0-149`, `150-299`, …), **max ~150 offres/appel**.
  Réponse `200` = complet, `206` = partiel (encore des pages), `204` = vide.
- Quota : **~4 appels/seconde par application** → mettre un `time.sleep(0.3)`.
- ⚠️ À CONFIRMER sur la doc Swagger (francetravail.io) avant de coder :
  l'**URL exacte du endpoint token** et le **scope** à demander. Ne pas inventer
  ces deux valeurs : me demander de les vérifier si elles manquent.

Champs JSON utiles par offre : `id`, `intitule`, `description`, `dateCreation`,
`lieuTravail` (commune/departement/coordonnées), `entreprise.nom`, `typeContrat`,
`experienceLibelle`, `salaire.libelle`, `competences[]`, `qualificationLibelle`,
`romeCode`/`romeLibelle`, `secteurActiviteLibelle`.

Périmètre de collecte : métiers Data/BI/IA via mots-clés (`data analyst`,
`data engineer`, `data scientist`, `business intelligence`, `BI`) et/ou codes
ROME, filtrés par région ou national, sur une fenêtre datée.

## 4. Stack technique

- Python 3.11+
- `requests` (appels API), `python-dotenv` (secrets)
- `pandas` (nettoyage / calculs)
- `matplotlib` + `seaborn` (visualisations)
- `jupyter` (notebook d'analyse)

## 5. Structure du dépôt

```
.
├── CLAUDE.md
├── README.md            # contexte, install, comment ré-exécuter
├── requirements.txt
├── .env.example         # variables attendues (sans valeurs)
├── .gitignore           # ignore .env, .venv/, data/raw/
├── data/
│   ├── raw/             # JSON bruts de l'API (NON versionné)
│   └── processed/       # CSV nettoyés (versionnés si légers)
├── src/
│   ├── 01_collecte.py   # auth + recherche paginée -> data/raw/
│   ├── 02_nettoyage.py  # data/raw -> data/processed
│   └── 03_calculs.py    # KPI et agrégats
├── notebooks/
│   └── 04_analyse.ipynb # visualisations + interprétation
└── rapport/
    └── rapport.pdf      # dossier final
```

## 6. Conventions

**Secrets** : identifiants API dans `.env` (jamais en clair, jamais commités).
Variables attendues :
```
FT_CLIENT_ID=
FT_CLIENT_SECRET=
FT_TOKEN_URL=        # à confirmer sur la doc
FT_SCOPE=            # à confirmer sur la doc
```
Toujours maintenir `.env.example` à jour (clés sans valeurs).

**Code** :
- Scripts numérotés et ré-exécutables de bout en bout, sans intervention manuelle.
- Pas de chemins absolus : utiliser des chemins relatifs depuis la racine du repo.
- Fonctions courtes, commentées en français.
- Gestion d'erreurs explicite sur les appels réseau (`raise_for_status`, retries).
- Respecter le quota API (`time.sleep`).

**Données** : `data/raw/` est immuable une fois collecté ; tout traitement
écrit dans `data/processed/`. Ne jamais modifier un fichier brut.

**Git** : commits petits et descriptifs en français (ex. `feat: collecte API`,
`fix: parsing salaire`). Binôme → privilégier des commits clairs pour se relire.

## 7. Commandes

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # puis remplir les identifiants

# Pipeline (dans l'ordre)
python src/01_collecte.py     # -> data/raw/
python src/02_nettoyage.py    # -> data/processed/
python src/03_calculs.py      # -> KPI / agrégats
jupyter notebook notebooks/04_analyse.ipynb
```

## 8. Question d'analyse (fil rouge du livrable IV)

« Quelles compétences Data sont les plus demandées en Île-de-France (ou en France)
et comment se valorisent-elles salarialement ? »
Toute l'analyse doit converger vers une réponse argumentée à cette question.

## 9. Points de vigilance connus

- `salaire.libelle` est souvent en **texte libre** ou absent → prévoir un parsing
  robuste (min/max, « selon profil ») et documenter le taux de valeurs manquantes.
- Dédoublonnage des offres par `id`.
- Limite de volumétrie totale de l'API : documenter combien d'offres ont été
  réellement récupérées et sur quel périmètre.
- Biais de la source (offres France Travail ≠ marché total) → à mentionner en
  conclusion (livrable V).

## 10. Façon de travailler attendue de Claude Code

- Procéder par **étapes claires**, valider chaque script avant de passer au suivant.
- Avant d'écrire du code qui dépend de valeurs API incertaines (token URL, scope),
  signaler le point et demander confirmation plutôt que d'inventer.
- Rappeler régulièrement le lien entre ce qui est codé et le **barème**.
