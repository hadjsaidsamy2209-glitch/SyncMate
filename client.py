"""
Phase 5 — Client de synchronisation.

Permet de tester la communication avec le serveur Flask depuis
n'importe quel appareil (PC en test local, ou Android via Termux).

Usage :
    python client.py --serveur http://100.x.x.1:5000 ping
    python client.py --serveur http://100.x.x.1:5000 fichiers
    python client.py --serveur http://100.x.x.1:5000 telecharger notes.txt
    python client.py --serveur http://100.x.x.1:5000 envoyer ./mon_fichier.txt documents/mon_fichier.txt
"""

import argparse
import sys
from pathlib import Path
import requests
from main import calculer_hash


def cmd_ping(serveur):
    reponse = requests.get(f"{serveur}/ping", timeout=5)
    reponse.raise_for_status()
    print("Serveur joignable :", reponse.json())


def cmd_fichiers(serveur):
    reponse = requests.get(f"{serveur}/fichiers", timeout=5)
    reponse.raise_for_status()
    fichiers = reponse.json()
    if not fichiers:
        print("Aucun fichier actif sur le serveur.")
        return
    print(f"{len(fichiers)} fichier(s) :")
    for f in fichiers:
        print(f"  [{f['statut'].upper()}] {f['chemin']}  ({f['taille']} octets)")


def cmd_telecharger(serveur, chemin_distant, destination=None):
    reponse = requests.get(f"{serveur}/telecharger/{chemin_distant}", timeout=30, stream=True)
    if reponse.status_code == 404:
        print(f"Fichier introuvable sur le serveur : {chemin_distant}")
        return
    reponse.raise_for_status()

    nom_local = destination or Path(chemin_distant).name
    with open(nom_local, "wb") as f:
        for morceau in reponse.iter_content(chunk_size=4096):
            f.write(morceau)
    reponse_hash = requests.get(f"{serveur}/hash/{chemin_distant}", timeout=5)
    hash_attendu = reponse_hash.json()["hash"]
    hash_recu = calculer_hash(nom_local)
    print(f"Fichier telecharge : {nom_local}")
    if hash_attendu == hash_recu:
         print("Transfert OK")
    else : 
         print("Transfert corrompu")
    


def cmd_envoyer(serveur, fichier_local, chemin_distant):
    fichier_local = Path(fichier_local)
    if not fichier_local.is_file():
        print(f"Fichier local introuvable : {fichier_local}")
        return

    with open(fichier_local, "rb") as f:
        reponse = requests.post(
            f"{serveur}/recevoir",
            data={"chemin": chemin_distant},
            files={"fichier": f},
            timeout=60,
        )
    reponse.raise_for_status()
    hash_server = reponse.json()["hash"]
    calcul_hash = calculer_hash(fichier_local)
    if hash_server == calcul_hash:
        print("Transfert OK")
    else: 
        print("Transfert corrompu")


# ---------------------------------------------------------------------------
# Entrée principale
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Client de synchronisation.")
    parser.add_argument("--serveur", default="http://localhost:5000", help="URL du serveur (defaut : http://localhost:5000)")

    sous_commandes = parser.add_subparsers(dest="commande")

    sous_commandes.add_parser("ping",     help="Verifier que le serveur repond")
    sous_commandes.add_parser("fichiers", help="Lister les fichiers actifs sur le serveur")

    p_dl = sous_commandes.add_parser("telecharger", help="Telecharger un fichier depuis le serveur")
    p_dl.add_argument("chemin",       help="Chemin relatif du fichier sur le serveur")
    p_dl.add_argument("destination",  nargs="?", help="Nom local de destination (optionnel)")

    p_send = sous_commandes.add_parser("envoyer", help="Envoyer un fichier vers le serveur")
    p_send.add_argument("fichier_local",   help="Chemin local du fichier a envoyer")
    p_send.add_argument("chemin_distant",  help="Chemin de destination sur le serveur")

    args = parser.parse_args()

    if args.commande is None:
        parser.print_help()
        sys.exit(1)

    try:
        if args.commande == "ping":
            cmd_ping(args.serveur)

        elif args.commande == "fichiers":
            cmd_fichiers(args.serveur)

        elif args.commande == "telecharger":
            cmd_telecharger(args.serveur, args.chemin, getattr(args, "destination", None))

        elif args.commande == "envoyer":
            cmd_envoyer(args.serveur, args.fichier_local, args.chemin_distant)

    except requests.exceptions.ConnectionError:
        print(f"Impossible de joindre le serveur : {args.serveur}")
        sys.exit(1)

    except requests.exceptions.HTTPError as e:
        print(f"Erreur HTTP : {e}")
        sys.exit(1)
