import ctypes
import time
import os
import sys
import threading
from sync import synchroniser
from watcher import demarrer
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


def lancer(dossier, dossier_smb, chemin_base, intervalle):
    t = threading.Thread(target=demarrer, args=(dossier, chemin_base), daemon=True)
    t.start()
    while True:
        synchroniser(dossier, dossier_smb, chemin_base)
        time.sleep(intervalle)


if __name__ == "__main__":
    config = charger_config()

    if config:
        dossier = config["dossier"]
        dossier_smb = config["dossier_smb"]
        devnull = open(os.devnull, "w", encoding="utf-8", errors="ignore")
        sys.stdout = devnull
        sys.stderr = devnull
    else:
        attacher_console()

        defaut = os.path.join(os.path.expanduser("~"), "SyncMate")
        print(f"Dossier local a synchroniser [{defaut}] : ", end="")
        dossier = input().strip() or defaut

        print("Chemin du dossier SMB (ex: \\\\mafreebox.freebox.fr\\Disque dur\\SyncMate) : ", end="")
        dossier_smb = input().strip()

        if not os.path.isdir(dossier_smb):
            print(f"\nImpossible d'acceder a {dossier_smb}")
            print("Verifiez que le partage SMB est monte et accessible.")
            time.sleep(5)
            sys.exit(1)

        sauvegarder_config(dossier, dossier_smb)
        enregistrer_demarrage()
        print("\nDemarrage automatique configure.")
        time.sleep(2)
        detacher_console()

    from database import NOM_BASE
    chemin_base = os.path.join(dossier, NOM_BASE)
    os.makedirs(dossier, exist_ok=True)

    lancer(
        dossier=dossier,
        dossier_smb=dossier_smb,
        chemin_base=chemin_base,
        intervalle=60,
    )
