import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from main import scanner_et_synchroniser_bdd
from database import NOM_BASE


class SyncHandler(FileSystemEventHandler):
    def __init__(self, dossier, chemin_base=NOM_BASE):
        self.dossier = dossier
        self.chemin_base = chemin_base

    def _synchroniser(self, src_path):
        try:
            scanner_et_synchroniser_bdd(self.dossier, chemin_base=self.chemin_base)
        except Exception:
            pass

    def on_created(self, event):
        if not event.is_directory:
            self._synchroniser(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._synchroniser(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._synchroniser(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._synchroniser(event.src_path)


def demarrer(dossier="./sync", chemin_base=NOM_BASE):
    handler = SyncHandler(dossier, chemin_base)
    observer = Observer()
    observer.schedule(handler, path=dossier, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
