import threading
import time
from unittest import mock

import watcher
from watcher import SyncHandler


class TestSyncEnCours:

    def test_events_ignores_pendant_sync(self, tmp_path):
        """Quand sync_en_cours est True, on_any_event ne planifie pas de scan."""
        handler = SyncHandler(str(tmp_path), chemin_base=str(tmp_path / "test.db"))
        watcher.sync_en_cours = True

        try:
            event = mock.MagicMock()
            event.is_directory = False
            event.src_path = str(tmp_path / "fichier.txt")

            handler.on_any_event(event)

            # _planifier_scan ne doit pas avoir ete appele -> pas de timer
            assert handler._timer is None
        finally:
            watcher.sync_en_cours = False

    def test_events_traites_hors_sync(self, tmp_path):
        """Quand sync_en_cours est False, on_any_event planifie un scan."""
        handler = SyncHandler(str(tmp_path), chemin_base=str(tmp_path / "test.db"))
        watcher.sync_en_cours = False

        event = mock.MagicMock()
        event.is_directory = False
        event.src_path = str(tmp_path / "fichier.txt")

        handler.on_any_event(event)

        assert handler._timer is not None
        handler._timer.cancel()

    def test_events_directory_ignores(self, tmp_path):
        """Les evenements de type directory sont ignores."""
        handler = SyncHandler(str(tmp_path), chemin_base=str(tmp_path / "test.db"))

        event = mock.MagicMock()
        event.is_directory = True
        event.src_path = str(tmp_path / "dossier")

        handler.on_any_event(event)

        assert handler._timer is None

    def test_events_syncmate_tmp_ignores(self, tmp_path):
        """Les evenements sur des fichiers .syncmate_tmp sont ignores."""
        handler = SyncHandler(str(tmp_path), chemin_base=str(tmp_path / "test.db"))

        event = mock.MagicMock()
        event.is_directory = False
        event.src_path = str(tmp_path / "copie.txt.syncmate_tmp")

        handler.on_any_event(event)

        assert handler._timer is None

    def test_executer_scan_ignore_si_sync_en_cours(self, tmp_path):
        """_executer_scan ne fait rien si sync_en_cours est True."""
        handler = SyncHandler(str(tmp_path), chemin_base=str(tmp_path / "test.db"))
        watcher.sync_en_cours = True

        try:
            with mock.patch("watcher.scanner_et_synchroniser_bdd") as mock_scan:
                handler._executer_scan()
                mock_scan.assert_not_called()
        finally:
            watcher.sync_en_cours = False

    def test_executer_scan_appelle_scanner_si_pas_sync(self, tmp_path):
        """_executer_scan appelle scanner_et_synchroniser_bdd normalement."""
        db = str(tmp_path / "test.db")
        handler = SyncHandler(str(tmp_path), chemin_base=db)
        watcher.sync_en_cours = False

        with mock.patch("watcher.scanner_et_synchroniser_bdd") as mock_scan:
            handler._executer_scan()
            mock_scan.assert_called_once_with(str(tmp_path), chemin_base=db)


class TestDebounce:

    def test_events_rapides_un_seul_scan(self, tmp_path):
        """Plusieurs events rapides ne declenchent qu'un seul scan."""
        db = str(tmp_path / "test.db")
        handler = SyncHandler(str(tmp_path), chemin_base=db)

        compteur = {"appels": 0}

        def faux_scan(*args, **kwargs):
            compteur["appels"] += 1

        with mock.patch("watcher.scanner_et_synchroniser_bdd", side_effect=faux_scan):
            # Envoyer 5 events rapidement
            for i in range(5):
                event = mock.MagicMock()
                event.is_directory = False
                event.src_path = str(tmp_path / f"fichier_{i}.txt")
                handler.on_any_event(event)

            # Attendre que le timer expire (5s de debounce + marge)
            time.sleep(6)

        # Un seul scan doit avoir eu lieu
        assert compteur["appels"] == 1

    def test_timer_annule_et_replanifie(self, tmp_path):
        """Chaque event annule le timer precedent et en cree un nouveau."""
        handler = SyncHandler(str(tmp_path), chemin_base=str(tmp_path / "test.db"))

        event1 = mock.MagicMock()
        event1.is_directory = False
        event1.src_path = str(tmp_path / "a.txt")
        handler.on_any_event(event1)
        timer1 = handler._timer

        event2 = mock.MagicMock()
        event2.is_directory = False
        event2.src_path = str(tmp_path / "b.txt")
        handler.on_any_event(event2)
        timer2 = handler._timer

        # Le timer doit avoir ete remplace
        assert timer1 is not timer2
        # L'ancien timer doit etre annule (finished = event interne du Timer)
        assert timer1.finished.is_set()

        timer2.cancel()
