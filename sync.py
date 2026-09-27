import sqlite3
import os
from datetime import datetime
from pathlib import Path

import requests

from database import NOM_BASE, creer_base
from main import scanner_et_synchroniser_bdd
from client import cmd_telecharger, cmd_envoyer


def lire_fichiers_locaux(chemin_base=NOM_BASE):
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


def lire_fichiers_distants(serveur, timeout=5):
    reponse = requests.get(f"{serveur}/fichiers", timeout=timeout)
    reponse.raise_for_status()
    return {f["chemin"]: f for f in reponse.json()}


def comparer_fichiers(locaux, distants):
    a_telecharger = []
    a_envoyer = []

    for chemin in set(locaux.keys()) | set(distants.keys()):
        local = locaux.get(chemin)
        distant = distants.get(chemin)

        if local is None or local["statut"] == "supprime":
            if distant is not None:
                a_telecharger.append(chemin)
            continue

        if distant is None:
            a_envoyer.append(chemin)
            continue

        if local["hash"] == distant["hash"]:
            continue

        date_locale = local["date_modification"] or ""
        date_distante = distant["date_modification"] or ""

        if date_locale > date_distante:
            a_envoyer.append(chemin)
        elif date_distante > date_locale:
            a_telecharger.append(chemin)
        else:
            a_envoyer.append(chemin)

    return {"a_telecharger": a_telecharger, "a_envoyer": a_envoyer, "conflits": []}


def synchroniser(serveur, dossier=None, chemin_base=NOM_BASE):
    if dossier:
        scanner_et_synchroniser_bdd(dossier, chemin_base=chemin_base)

    locaux = lire_fichiers_locaux(chemin_base)

    try:
        distants = lire_fichiers_distants(serveur)
    except requests.exceptions.ConnectionError:
        print(f"Impossible de joindre le serveur : {serveur}")
        return

    actions = comparer_fichiers(locaux, distants)
    total = len(actions["a_telecharger"]) + len(actions["a_envoyer"])

    if total == 0:
        print("Tout est deja synchronise.")
        return

    if actions["a_telecharger"]:
        print(f"\nFichiers a telecharger ({len(actions['a_telecharger'])}) :")
        for chemin in actions["a_telecharger"]:
            print(f"  [TELECHARGE] {chemin}")
            destination = str(Path(dossier) / chemin) if dossier else chemin
            Path(destination).parent.mkdir(parents=True, exist_ok=True)
            cmd_telecharger(serveur, chemin, destination)
            date_serveur = distants[chemin].get("date_modification")
            if date_serveur:
                try:
                    ts = datetime.fromisoformat(date_serveur).timestamp()
                    os.utime(destination, (ts, ts))
                except Exception:
                    pass

    if actions["a_envoyer"]:
        print(f"\nFichiers a envoyer ({len(actions['a_envoyer'])}) :")
        for chemin in actions["a_envoyer"]:
            print(f"  [ENVOYE] {chemin}")
            fichier_local = str(Path(dossier) / chemin) if dossier else chemin
            cmd_envoyer(serveur, fichier_local, chemin)

    print("\nSynchronisation terminee.")
