import ctypes
import time
import os
import sys
import threading
from sync import synchroniser
from watcher import demarrer
from tailscale import choisir_serveur, choisir_dossier
from config import charger_config, sauvegarder_config


def attacher_console():
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.kernel32.AllocConsole()
        sys.stdin = open("CONIN$", "r")
        sys.stdout = open("CONOUT$", "w")
        sys.stderr = open("CONOUT$", "w")
    except Exception:
        pass


def detacher_console():
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.kernel32.FreeConsole()
        devnull = open(os.devnull, "w", encoding="utf-8", errors="ignore")
        sys.stdout = devnull
        sys.stderr = devnull
        sys.stdin = open(os.devnull, "r")
    except Exception:
        pass


def enregistrer_demarrage():
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return
    try:
        exe = sys.executable
        startup = os.path.join(
            os.environ["APPDATA"],
            r"Microsoft\Windows\Start Menu\Programs\Startup"
        )
        vbs = os.path.join(startup, "SyncMate.vbs")
        with open(vbs, "w") as f:
            f.write(f'CreateObject("WScript.Shell").Run "{exe}", 0, False\n')
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
        devnull = open(os.devnull, "w", encoding="utf-8", errors="ignore")
        sys.stdout = devnull
        sys.stderr = devnull
    else:
        attacher_console()
        serveur = choisir_serveur()
        dossier = choisir_dossier()
        sauvegarder_config(dossier, serveur)
        enregistrer_demarrage()
        print("\nDemarrage automatique configure.")
        time.sleep(2)
        detacher_console()

    chemin_base = os.path.join(dossier, "samyai.db")
    os.makedirs(dossier, exist_ok=True)

    lancer(
        serveur=serveur,
        dossier=dossier,
        chemin_base=chemin_base,
        intervalle=60,
    )
