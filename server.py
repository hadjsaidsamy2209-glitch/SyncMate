import argparse
import threading
from pathlib import Path
from flask import Flask, jsonify, send_file, request, abort
import sqlite3
from main import calculer_hash, scanner_et_synchroniser_bdd
from database import NOM_BASE, creer_base
from watcher import demarrer

app = Flask(__name__)

DOSSIER_SYNC = "./sync"
CHEMIN_BASE = NOM_BASE


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
    parser = argparse.ArgumentParser()
    parser.add_argument("--dossier", default="./sync")
    parser.add_argument("--port", default=5000, type=int)
    parser.add_argument("--base", default=NOM_BASE)
    args = parser.parse_args()

    DOSSIER_SYNC = args.dossier
    CHEMIN_BASE = args.base

    creer_base(CHEMIN_BASE)
    scanner_et_synchroniser_bdd(DOSSIER_SYNC, chemin_base=CHEMIN_BASE)

    t = threading.Thread(target=demarrer, args=(DOSSIER_SYNC, CHEMIN_BASE), daemon=True)
    t.start()

    print(f"Dossier : {DOSSIER_SYNC}")
    print(f"Serveur : http://0.0.0.0:{args.port}")

    app.run(host="0.0.0.0", port=args.port, debug=False)
