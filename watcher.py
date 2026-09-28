import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from main import scanner_et_synchroniser_bdd
from database import NOM_BASE

sync_en_cours = False


class SyncHandler(FileSystemEventHandler):
    def __init__(self, dossier, chemin_base=NOM_BASE):
        self.dossier = dossier
        self.chemin_base = chemin_base
        self._timer = None
        self._lock = threading.Lock()

    def _planifier_scan(self):
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(5, self._executer_scan)
            self._timer.start()

    def _executer_scan(self):
        if sync_en_cours:
            return
        try:
            scanner_et_synchroniser_bdd(self.dossier, chemin_base=self.chemin_base)
        except Exception:
            pass

    def on_any_event(self, event):
        if event.is_directory:
            return
        if sync_en_cours:
            return
        src = getattr(event, "src_path", "")
        if ".syncmate_tmp" in src:
            return
        self._planifier_scan()


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
