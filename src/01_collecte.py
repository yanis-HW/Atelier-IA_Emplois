"""01_collecte.py — Collecte des offres d'emploi Data en Île-de-France.

Livrable I (Plan de récolte de données, 5 pts).

Pipeline :
  1. Authentification OAuth2 (client_credentials) sur l'API France Travail.
  2. Recherche paginée des offres pour une liste de mots-clés Data/BI/IA,
     filtrée sur l'Île-de-France (départements 75/77/78/91/92/93/94/95).
  3. Écriture des réponses JSON brutes, horodatées, dans data/raw/.

Les fichiers de data/raw/ sont IMMUABLES : tout traitement ultérieur lit ces
fichiers sans les modifier (cf. CLAUDE.md §6).

Ré-exécutable de bout en bout : `python src/01_collecte.py`
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

# --- Constantes de collecte -------------------------------------------------

# Racine du dépôt, calculée relativement à ce fichier (pas de chemin absolu).
RACINE = Path(__file__).resolve().parent.parent
DOSSIER_RAW = RACINE / "data" / "raw"

# Affichage des accents correct dans la console Windows (sortie en UTF-8).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

URL_RECHERCHE = (
    "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
)

# Filtre géographique : région Île-de-France (code région 11).
# On utilise `region` plutôt que `departement` car l'API limite ce dernier à
# 5 valeurs, or l'IDF compte 8 départements. Le département reste disponible
# dans chaque offre retournée (lieuTravail) pour l'analyse fine.
REGION_IDF = "11"

# Mots-clés métiers Data/BI/IA. Un fichier brut par mot-clé pour tracer la source.
MOTS_CLES = [
    "data analyst",
    "data engineer",
    "data scientist",
    "business intelligence",
    "BI",
]

# Fenêtre temporelle de collecte (offres créées sur les N derniers jours).
FENETRE_JOURS = 30

# Pagination (paramètre `range=p-d`) : plage limitée à 150 résultats par appel.
TAILLE_PAGE = 150
# Bornes imposées par l'API : l'index de début `p` <= 3000 et l'index de fin
# `d` <= 3149. On ne peut donc pas récupérer plus de ~3150 offres par requête.
INDEX_DEBUT_MAX = 3000
INDEX_FIN_MAX = 3149
# Respect du quota (~4 appels/seconde par application) : pause entre deux appels.
PAUSE_SECONDES = 0.3


# --- Configuration & authentification ---------------------------------------

def charger_config() -> dict:
    """Charge les identifiants API depuis le fichier .env."""
    load_dotenv(RACINE / ".env")
    config = {
        "client_id": os.getenv("FT_CLIENT_ID"),
        "client_secret": os.getenv("FT_CLIENT_SECRET"),
        "token_url": os.getenv("FT_TOKEN_URL"),
        "scope": os.getenv("FT_SCOPE"),
    }
    manquantes = [cle for cle, val in config.items() if not val]
    if manquantes:
        raise RuntimeError(
            "Variables d'environnement manquantes dans .env : "
            + ", ".join(manquantes)
            + ". Copier .env.example en .env puis renseigner les identifiants."
        )
    return config


def obtenir_token(config: dict) -> str:
    """Récupère un jeton d'accès OAuth2 via le grant client_credentials."""
    reponse = requests.post(
        config["token_url"],
        data={
            "grant_type": "client_credentials",
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "scope": config["scope"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    reponse.raise_for_status()
    return reponse.json()["access_token"]


# --- Recherche paginée -------------------------------------------------------

def _total_depuis_content_range(entete: str | None) -> int | None:
    """Extrait le nombre total d'offres de l'en-tête Content-Range.

    Format attendu : "offres 0-149/3456" -> 3456.
    """
    if not entete or "/" not in entete:
        return None
    try:
        return int(entete.rsplit("/", 1)[1])
    except ValueError:
        return None


def _appel_page(token: str, mot_cle: str, debut: int,
                date_min: str, date_max: str) -> requests.Response:
    """Effectue un appel de recherche pour une page (un intervalle `range`)."""
    # On borne l'index de fin pour respecter la limite d <= 3149 de l'API.
    fin = min(debut + TAILLE_PAGE - 1, INDEX_FIN_MAX)
    params = {
        "motsCles": mot_cle,
        "region": REGION_IDF,
        "minCreationDate": date_min,
        "maxCreationDate": date_max,
        "range": f"{debut}-{fin}",
    }
    entetes = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    # Petite politique de retry sur 429 (quota) et 5xx (erreurs serveur).
    for tentative in range(4):
        reponse = requests.get(URL_RECHERCHE, params=params,
                               headers=entetes, timeout=30)
        if reponse.status_code in (429, 500, 502, 503, 504):
            attente = PAUSE_SECONDES * (tentative + 1) * 3
            print(f"    HTTP {reponse.status_code}, nouvelle tentative "
                  f"dans {attente:.1f}s...")
            time.sleep(attente)
            continue
        return reponse
    reponse.raise_for_status()
    return reponse


def rechercher_offres(token: str, mot_cle: str,
                      date_min: str, date_max: str) -> list[dict]:
    """Récupère toutes les offres d'un mot-clé en parcourant les pages.

    Codes HTTP : 200 = page complète (fin), 206 = page partielle (continuer),
    204 = aucune offre.
    """
    offres: list[dict] = []
    debut = 0
    while debut <= INDEX_DEBUT_MAX:
        fin = min(debut + TAILLE_PAGE - 1, INDEX_FIN_MAX)
        reponse = _appel_page(token, mot_cle, debut, date_min, date_max)

        if reponse.status_code == 204:  # aucune offre
            break
        reponse.raise_for_status()

        lot = reponse.json().get("resultats", [])
        if not lot:
            break
        offres.extend(lot)

        total = _total_depuis_content_range(reponse.headers.get("Content-Range"))
        print(f"    range {debut}-{fin} : "
              f"+{len(lot)} offres (total source : {total})")

        # 200 = dernière page atteinte ; 206 = il reste des pages à parcourir.
        if reponse.status_code == 200:
            break
        if total is not None and fin + 1 >= total:
            break
        if fin >= INDEX_FIN_MAX:  # plafond de volumétrie de l'API atteint
            print("    Plafond API (3150 offres) atteint pour ce mot-clé.")
            break

        debut += TAILLE_PAGE
        time.sleep(PAUSE_SECONDES)

    return offres


# --- Écriture des données brutes --------------------------------------------

def sauvegarder_brut(mot_cle: str, offres: list[dict], horodatage: str) -> Path:
    """Écrit les offres d'un mot-clé dans un JSON brut horodaté."""
    DOSSIER_RAW.mkdir(parents=True, exist_ok=True)
    slug = mot_cle.replace(" ", "_")
    chemin = DOSSIER_RAW / f"offres_{slug}_{horodatage}.json"
    contenu = {
        "mot_cle": mot_cle,
        "region": REGION_IDF,
        "collecte_le": horodatage,
        "nb_offres": len(offres),
        "resultats": offres,
    }
    chemin.write_text(json.dumps(contenu, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    return chemin


# --- Orchestration -----------------------------------------------------------

def main() -> None:
    config = charger_config()
    print("Authentification OAuth2...")
    token = obtenir_token(config)
    print("Token obtenu.\n")

    maintenant = datetime.now(timezone.utc)
    date_max = maintenant.strftime("%Y-%m-%dT%H:%M:%SZ")
    date_min = (maintenant - timedelta(days=FENETRE_JOURS)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    horodatage = maintenant.strftime("%Y%m%d_%H%M%S")
    print(f"Périmètre : Île-de-France (region={REGION_IDF})")
    print(f"Fenêtre   : {date_min} -> {date_max}\n")

    total_collecte = 0
    for mot_cle in MOTS_CLES:
        print(f"[{mot_cle}]")
        offres = rechercher_offres(token, mot_cle, date_min, date_max)
        chemin = sauvegarder_brut(mot_cle, offres, horodatage)
        total_collecte += len(offres)
        print(f"  -> {len(offres)} offres écrites dans {chemin.name}\n")
        time.sleep(PAUSE_SECONDES)

    print(f"Terminé : {total_collecte} offres collectées (avant dédoublonnage).")


if __name__ == "__main__":
    main()
