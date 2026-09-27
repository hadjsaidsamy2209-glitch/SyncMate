"""
Phase 5 — Serveur Flask sur le PC.

Expose l'état de la BDD et les fichiers du dossier surveillé
via une API HTTP simple. L'Android (ou tout autre appareil
sur le même réseau / Tailscale) peut interroger ce serveur.

Usage :
    python server.py
    python server.py --dossier ./test --port 5000
"""

import argparse
from pathlib import Path
from flask import Flask, jsonify, send_file, request, abort
import sqlite3
from main import calculer_hash
from database import NOM_BASE, creer_base

app = Flask(__name__)

# Paramètres globaux modifiés au démarrage via argparse
DOSSIER_SYNC = "./test"
CHEMIN_BASE  = NOM_BASE


# ---------------------------------------------------------------------------
# GET /ping
# ---------------------------------------------------------------------------

@app.route("/ping")
def ping():
    """Vérifie que le serveur est joignable."""
    return jsonify({"statut": "ok"})


# ---------------------------------------------------------------------------
# GET /fichiers
# ---------------------------------------------------------------------------

@app.route("/fichiers")
def liste_fichiers():
    """Renvoie tous les fichiers actifs connus de la BDD (statut != supprime)."""
    connexion = sqlite3.connect(CHEMIN_BASE, timeout=10)
    connexion.row_factory = sqlite3.Row #envoie des objets en dictionnaires au lieu de tuples""
    curseur = connexion.cursor() #créer le stylo pour manip la table sql""
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


# ---------------------------------------------------------------------------
# GET /telecharger/<chemin>
# ---------------------------------------------------------------------------

@app.route("/telecharger/<path:chemin>")
def telecharger(chemin):
    """Envoie le fichier demandé au client.

    <chemin> est le chemin relatif par rapport au dossier surveillé.
    Exemple : GET /telecharger/documents/notes.txt
    """
    fichier = Path(DOSSIER_SYNC) / chemin

    # Sécurité : on s'assure que le chemin résolu reste bien dans DOSSIER_SYNC.
    # Sans ça, un client malveillant pourrait demander "../../passwords.txt".
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
    curseur.execute("""SELECT hash FROM fichiers WHERE chemin = ?""" , (chemin,)
    )
    ligne = curseur.fetchone()
    connexion.close()
    if not ligne :
        abort(404)
    return jsonify({"hash": ligne[0]})
# ---------------------------------------------------------------------------
# POST /recevoir
# ---------------------------------------------------------------------------

@app.route("/recevoir", methods=["POST"])
def recevoir():
    """Reçoit un fichier envoyé par l'Android et le sauvegarde dans DOSSIER_SYNC.

    Le client doit envoyer :
      - un champ de formulaire  "chemin"  : chemin relatif de destination
      - un fichier              "fichier" : le contenu binaire
    """
    if "fichier" not in request.files:
        abort(400)
    if "chemin" not in request.form:
        abort(400)

    chemin_relatif = request.form["chemin"]
    fichier_recu   = request.files["fichier"]

    destination = Path(DOSSIER_SYNC) / chemin_relatif

    # Même vérification de sécurité que pour le téléchargement.
    try:
        destination.resolve().relative_to(Path(DOSSIER_SYNC).resolve())
    except ValueError:
        abort(403)

    destination.parent.mkdir(parents=True, exist_ok=True)
    fichier_recu.save(destination)
    hash_recu = calculer_hash(destination)
    return jsonify({"statut": "ok", "chemin": chemin_relatif,"hash" :hash_recu}), 201



    
# ---------------------------------------------------------------------------
# Démarrage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import threading
    from watcher import demarrer

    parser = argparse.ArgumentParser(description="Serveur de synchronisation PC.")
    parser.add_argument("--dossier", default="./test",   help="Dossier synchronise (defaut : ./test)")
    parser.add_argument("--port",    default=5000, type=int, help="Port d'ecoute (defaut : 5000)")
    parser.add_argument("--base",    default=NOM_BASE,   help="Chemin de la base SQLite")
    args = parser.parse_args()

    DOSSIER_SYNC = args.dossier
    CHEMIN_BASE  = args.base

    creer_base(CHEMIN_BASE)

    # Scan initial pour mettre la DB à jour au démarrage
    from main import scanner_et_synchroniser_bdd
    scanner_et_synchroniser_bdd(DOSSIER_SYNC, chemin_base=CHEMIN_BASE)

    # Watcher en arrière-plan pour détecter les changements en temps réel
    t = threading.Thread(target=demarrer, args=(DOSSIER_SYNC, CHEMIN_BASE), daemon=True)
    t.start()

    print(f"Dossier surveille : {DOSSIER_SYNC}")
    print(f"Base de donnees   : {CHEMIN_BASE}")
    print(f"Serveur demarre   : http://0.0.0.0:{args.port}")
    print("Ctrl+C pour arreter.\n")

    app.run(host="0.0.0.0", port=args.port, debug=False)
