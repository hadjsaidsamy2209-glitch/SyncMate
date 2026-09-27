import ctypes
import os
import sys
import threading
from pathlib import Path
from flask import Flask, jsonify, send_file, request, abort
import sqlite3
from main import calculer_hash, scanner_et_synchroniser_bdd
from database import NOM_BASE, creer_base
from watcher import demarrer
from config import charger_config, sauvegarder_config, _chemin_config

app = Flask(__name__)

DOSSIER_SYNC = "./sync"
CHEMIN_BASE = NOM_BASE


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
        vbs = os.path.join(startup, "SyncMateServer.vbs")
        with open(vbs, "w") as f:
            f.write(f'CreateObject("WScript.Shell").Run "{exe}", 0, False\n')
    except Exception:
        pass


@app.route("/ping")
def ping():
    return jsonify({"statut": "ok"})


@app.route("/fichiers")
def liste_fichiers():
    connexion = sqlite3.connect(CHEMIN_BASE, timeout=10)
    connexion.row_factory = sqlite3.Row
    curseur = connexion.cursor()
    curseur.execute("""
        SELECT nom, chemin, extension, taille, date_modification, hash, appareil, statut
        FROM fichiers
        WHERE statut != 'supprime'
          AND extension NOT IN ('db', 'db-shm', 'db-wal', 'db-journal')
        ORDER BY chemin
    """)
    lignes = [dict(ligne) for ligne in curseur.fetchall()]
    connexion.close()
    return jsonify(lignes)


@app.route("/telecharger/<path:chemin>")
def telecharger(chemin):
    fichier = Path(DOSSIER_SYNC) / chemin
    try:
        fichier.resolve().relative_to(Path(DOSSIER_SYNC).resolve())
    except ValueError:
        abort(403)
    if not fichier.is_file():
        abort(404)
    return send_file(fichier.resolve(), as_attachment=True)


@app.route("/hash/<path:chemin>")
def get_hash(chemin):
    connexion = sqlite3.connect(CHEMIN_BASE, timeout=10)
    curseur = connexion.cursor()
    curseur.execute("SELECT hash FROM fichiers WHERE chemin = ?", (chemin,))
    ligne = curseur.fetchone()
    connexion.close()
    if not ligne:
        abort(404)
    return jsonify({"hash": ligne[0]})


@app.route("/recevoir", methods=["POST"])
def recevoir():
    if "fichier" not in request.files or "chemin" not in request.form:
        abort(400)

    chemin_relatif = request.form["chemin"]
    fichier_recu = request.files["fichier"]
    destination = Path(DOSSIER_SYNC) / chemin_relatif

    try:
        destination.resolve().relative_to(Path(DOSSIER_SYNC).resolve())
    except ValueError:
        abort(403)

    destination.parent.mkdir(parents=True, exist_ok=True)
    fichier_recu.save(destination)
    return jsonify({"statut": "ok", "chemin": chemin_relatif, "hash": calculer_hash(destination)}), 201


if __name__ == "__main__":
    NOM_CFG = "server_config.json"
    config = charger_config(NOM_CFG)

    if config:
        dossier = config.get("dossier", "./sync")
        devnull = open(os.devnull, "w", encoding="utf-8", errors="ignore")
        sys.stdout = devnull
        sys.stderr = devnull
    else:
        attacher_console()
        defaut = str(Path.home() / "SyncMate")
        print(f"\nDossier a synchroniser (Entree = {defaut}) : ", end="")
        saisie = input().strip()
        dossier = saisie if saisie else defaut
        sauvegarder_config(dossier, "server", NOM_CFG)
        enregistrer_demarrage()
        print("\nDemarrage automatique configure.")
        import time
        time.sleep(2)
        detacher_console()

    DOSSIER_SYNC = dossier
    CHEMIN_BASE = os.path.join(dossier, "samyai.db")

    os.makedirs(DOSSIER_SYNC, exist_ok=True)
    creer_base(CHEMIN_BASE)
    scanner_et_synchroniser_bdd(DOSSIER_SYNC, chemin_base=CHEMIN_BASE)

    t = threading.Thread(target=demarrer, args=(DOSSIER_SYNC, CHEMIN_BASE), daemon=True)
    t.start()

    app.run(host="0.0.0.0", port=5000, debug=False)
