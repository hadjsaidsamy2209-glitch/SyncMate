import time
import os
import sys
import threading
from sync import synchroniser
from watcher import demarrer
from tailscale import choisir_serveur, choisir_dossier
from config import charger_config, sauvegarder_config


def enregistrer_demarrage():
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return
    try:
        import winreg
        exe = sys.executable
        cle = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(cle, "SyncMate", 0, winreg.REG_SZ, exe)
        winreg.CloseKey(cle)
    except Exception:
        pass


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
        print(f"Connexion a {serveur} | Dossier : {dossier}")
    else:
        serveur = choisir_serveur()
        dossier = choisir_dossier()
        sauvegarder_config(dossier, serveur)
        enregistrer_demarrage()
        print("\nDemarrage automatique configure.")

    chemin_base = os.path.join(dossier, "samyai.db")
    os.makedirs(dossier, exist_ok=True)

    print(f"\nDemarrage — {serveur}\n")

    lancer(
        serveur=serveur,
        dossier=dossier,
        chemin_base=chemin_base,
        intervalle=60,
    )
