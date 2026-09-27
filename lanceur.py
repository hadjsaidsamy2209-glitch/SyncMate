import time
import os
import threading
from sync import synchroniser
from watcher import demarrer
from tailscale import choisir_serveur, choisir_dossier
from config import charger_config, sauvegarder_config


def lancer(serveur, dossier, chemin_base, intervalle):
    t = threading.Thread(target=demarrer, args=(dossier, chemin_base), daemon=True)
    t.start()
    while True:
        synchroniser(serveur, dossier, chemin_base)
        time.sleep(intervalle)


if __name__ == "__main__":
    config = charger_config()

    if config:
        serveur = config["serveur"]
        dossier = config["dossier"]
        print(f"Configuration chargee : {serveur} | {dossier}")
    else:
        serveur = choisir_serveur()
        dossier = choisir_dossier()
        sauvegarder_config(dossier, serveur)

    chemin_base = os.path.join(dossier, "samyai.db")
    os.makedirs(dossier, exist_ok=True)

    print(f"\nDemarrage de la synchronisation avec {serveur}...")
    print(f"Dossier : {dossier}\n")

    lancer(
        serveur     = serveur,
        dossier     = dossier,
        chemin_base = chemin_base,
        intervalle  = 60,
    )
