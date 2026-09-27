"""
Phase 4 — Surveillance automatique du dossier synchronisé.

Lance ce fichier pour surveiller le dossier en temps réel.
Dès qu'un fichier est créé, modifié, supprimé ou déplacé,
la base SQLite est mise à jour automatiquement.

Usage :
    python watcher.py
    python watcher.py --dossier ./mon_dossier
"""

import time
import argparse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from main import scanner_et_synchroniser_bdd
from database import NOM_BASE

LABELS = {
    "nouveau":  "NOUVEAU",
    "modifie":  "MODIFIE",
    "supprime": "SUPPRIME",
}


class SyncHandler(FileSystemEventHandler):
    """Réagit aux événements du système de fichiers et met à jour la BDD."""

    def __init__(self, dossier, chemin_base=NOM_BASE):
        self.dossier = dossier
        self.chemin_base = chemin_base

    def _synchroniser(self, src_path):
        """Déclenche un scan et affiche les changements détectés."""
        try:
            changements = scanner_et_synchroniser_bdd(self.dossier, chemin_base=self.chemin_base)
            for c in changements:
                label = LABELS.get(c["action"], c["action"].upper())
                print(f"  [{label}] {c['chemin']}")
        except Exception:
            # BDD occupée par la sync réseau → la prochaine sync prendra en compte ce changement
            pass

    def on_created(self, event):
        if event.is_directory:
            return
        print(f"\nFichier cree : {event.src_path}")
        self._synchroniser(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        print(f"\nFichier modifie : {event.src_path}")
        self._synchroniser(event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        print(f"\nFichier supprime : {event.src_path}")
        self._synchroniser(event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            return
        # Un renommage = l'ancien chemin disparaît + le nouveau apparaît.
        # scanner_et_synchroniser_bdd() gère les deux automatiquement.
        print(f"\nFichier renomme : {event.src_path} -> {event.dest_path}")
        self._synchroniser(event.src_path)


def demarrer(dossier="./test", chemin_base=NOM_BASE):
    """Démarre la surveillance du dossier. Bloque jusqu'à Ctrl+C."""
    handler = SyncHandler(dossier, chemin_base)
    observer = Observer()
    observer.schedule(handler, path=dossier, recursive=True)
    observer.start()

    print(f"Surveillance active : {dossier}")
    print("Appuie sur Ctrl+C pour arreter.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nArret de la surveillance...")
        observer.stop()

    observer.join()
    print("Surveillance arretee.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Surveillance automatique du dossier synchronise.")
    parser.add_argument(
        "--dossier",
        default="./test",
        help="Dossier a surveiller (defaut : ./test)",
    )
    args = parser.parse_args()
    demarrer(dossier=args.dossier)
