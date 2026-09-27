from pathlib import Path
import requests
from main import calculer_hash


def cmd_ping(serveur):
    reponse = requests.get(f"{serveur}/ping", timeout=5)
    reponse.raise_for_status()


def cmd_fichiers(serveur):
    reponse = requests.get(f"{serveur}/fichiers", timeout=5)
    reponse.raise_for_status()
    return reponse.json()


def cmd_telecharger(serveur, chemin_distant, destination=None):
    reponse = requests.get(f"{serveur}/telecharger/{chemin_distant}", timeout=30, stream=True)
    if reponse.status_code == 404:
        return
    reponse.raise_for_status()

    nom_local = destination or Path(chemin_distant).name
    with open(nom_local, "wb") as f:
        for morceau in reponse.iter_content(chunk_size=4096):
            f.write(morceau)

    reponse_hash = requests.get(f"{serveur}/hash/{chemin_distant}", timeout=5)
    hash_attendu = reponse_hash.json()["hash"]
    hash_recu = calculer_hash(nom_local)
    if hash_attendu != hash_recu:
        print(f"  [AVERTISSEMENT] Transfert corrompu : {chemin_distant}")


def cmd_envoyer(serveur, fichier_local, chemin_distant):
    fichier_local = Path(fichier_local)
    if not fichier_local.is_file():
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
    if hash_server != calculer_hash(fichier_local):
        print(f"  [AVERTISSEMENT] Transfert corrompu : {chemin_distant}")
