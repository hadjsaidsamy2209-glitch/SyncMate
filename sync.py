"""
Phase 6 — Synchronisation bidirectionnelle PC ↔ PC.

Compare la BDD locale avec la liste des fichiers du serveur distant,
puis transfère ce qui a changé dans les deux sens.

Usage :
    python sync.py
    python sync.py --serveur http://100.x.x.1:5000 --dossier ./test
"""

import argparse
import sqlite3
import os
from datetime import datetime
from pathlib import Path

import requests

from database import NOM_BASE, creer_base
from main import scanner_et_synchroniser_bdd
from client import cmd_telecharger, cmd_envoyer


# ---------------------------------------------------------------------------
# Lecture de la BDD locale
# ---------------------------------------------------------------------------

def lire_fichiers_locaux(chemin_base=NOM_BASE):
    """Renvoie un dictionnaire {chemin: infos} des fichiers actifs en local."""
    connexion = sqlite3.connect(chemin_base, timeout=30)
    connexion.execute("PRAGMA journal_mode=WAL")
    connexion.row_factory = sqlite3.Row
    curseur = connexion.cursor()
    curseur.execute("""
        SELECT chemin, hash, taille, date_modification, statut, appareil
        FROM fichiers
    """)
    fichiers = {ligne["chemin"]: dict(ligne) for ligne in curseur.fetchall()}
    connexion.close()
    return fichiers


# ---------------------------------------------------------------------------
# Lecture de la BDD distante
# ---------------------------------------------------------------------------

def lire_fichiers_distants(serveur, timeout=5):
    """Récupère la liste des fichiers du serveur distant via /fichiers."""
    reponse = requests.get(f"{serveur}/fichiers", timeout=timeout)
    reponse.raise_for_status()
    fichiers = reponse.json()
    return {f["chemin"]: f for f in fichiers}




def comparer_fichiers(locaux, distants):
    """Compare les deux dictionnaires et renvoie les actions à effectuer.

    Retourne un dictionnaire avec trois listes :
    - a_telecharger : fichiers à récupérer depuis le serveur
    - a_envoyer     : fichiers à envoyer au serveur
    - conflits      : fichiers modifiés des deux côtés (hash différent, pas de gagnant évident)
    """
    a_telecharger = []
    a_envoyer     = []
    conflits      = []

    tous_les_chemins = set(locaux.keys()) | set(distants.keys())

    for chemin in tous_les_chemins:
        local   = locaux.get(chemin)
        distant = distants.get(chemin)

        # Cas 1 : fichier supprimé localement mais actif au loin → télécharger
        if local is None or local["statut"] == "supprime":
            if distant is not None:
                a_telecharger.append(chemin)
            continue

        # Cas 2 : fichier actif localement mais absent au loin → envoyer
        if distant is None:
            a_envoyer.append(chemin)
            continue

        # Cas 3 : fichier présent des deux côtés
        if local["hash"] == distant["hash"]:
            continue  # identiques → rien à faire

        # Hash différent : on compare les dates pour savoir lequel est plus récent
        date_locale   = local["date_modification"]  or ""
        date_distante = distant["date_modification"] or ""

        if date_locale > date_distante:
            a_envoyer.append(chemin)
        elif date_distante > date_locale:
            a_telecharger.append(chemin)
        else:
            # Même date, hash différent → le local gagne (tiebreaker)
            a_envoyer.append(chemin)

    return {
        "a_telecharger": a_telecharger,
        "a_envoyer":     a_envoyer,
        "conflits":      [],
    }


# ---------------------------------------------------------------------------
# Synchronisation complète
# ---------------------------------------------------------------------------

def synchroniser(serveur, dossier=None, chemin_base=NOM_BASE):
    """Lance un cycle complet de synchronisation avec le serveur distant."""

    print(f"Synchronisation avec : {serveur}")

    # 1. Scan local pour mettre la BDD à jour avant de comparer
    if dossier:
        print("Scan local en cours...")
        scanner_et_synchroniser_bdd(dossier, chemin_base=chemin_base)

    # 2. Lire les deux listes
    print("Lecture de la BDD locale...")
    locaux = lire_fichiers_locaux(chemin_base)

    print("Lecture des fichiers distants...")
    try:
        distants = lire_fichiers_distants(serveur)
    except requests.exceptions.ConnectionError:
        print(f"Impossible de joindre le serveur : {serveur}")
        return

    # 3. Comparer
    actions = comparer_fichiers(locaux, distants)

    total = len(actions["a_telecharger"]) + len(actions["a_envoyer"]) + len(actions["conflits"])
    if total == 0:
        print("Tout est deja synchronise.")
        return

    # 4. Télécharger ce qui manque localement
    if actions["a_telecharger"]:
        print(f"\nFichiers a telecharger ({len(actions['a_telecharger'])}) :")
        for chemin in actions["a_telecharger"]:
            print(f"  [TELECHARGE] {chemin}")
            destination = str(Path(dossier) / chemin) if dossier else chemin
            Path(destination).parent.mkdir(parents=True, exist_ok=True)
            cmd_telecharger(serveur, chemin, destination)
            # Restaure la date de modification du serveur pour éviter les faux conflits
            date_serveur = distants[chemin].get("date_modification")
            if date_serveur:
                try:
                    ts = datetime.fromisoformat(date_serveur).timestamp()
                    os.utime(destination, (ts, ts))
                except Exception:
                    pass

    # 5. Envoyer ce qui manque au serveur
    if actions["a_envoyer"]:
        print(f"\nFichiers a envoyer ({len(actions['a_envoyer'])}) :")
        for chemin in actions["a_envoyer"]:
            print(f"  [ENVOYE] {chemin}")
            fichier_local = str(Path(dossier) / chemin) if dossier else chemin
            cmd_envoyer(serveur, fichier_local, chemin)

    print("\nSynchronisation terminee.")




# ---------------------------------------------------------------------------
# Démarrage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synchronisation bidirectionnelle PC <-> PC.")
    parser.add_argument("--serveur", default="http://localhost:5000", help="URL du serveur distant")
    parser.add_argument("--dossier", default="./test",               help="Dossier local a synchroniser")
    parser.add_argument("--base",    default=NOM_BASE,               help="Chemin de la base SQLite locale")
    args = parser.parse_args()

    synchroniser(
        serveur     = args.serveur,
        dossier     = args.dossier,
        chemin_base = args.base,
    )
