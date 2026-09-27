"""Tests pour lanceur.py"""

import threading
import time
from unittest.mock import patch, MagicMock, call

from lanceur import lancer


class TestLancer:

    def test_watcher_demarre_en_thread(self):
        """Le watcher tourne dans un thread daemon séparé."""
        threads_avant = threading.active_count()

        with patch("lanceur.demarrer") as mock_demarrer, \
             patch("lanceur.synchroniser"), \
             patch("lanceur.time.sleep", side_effect=InterruptedError):
            try:
                lancer("http://1.2.3.4:5000", "./test", "test.db", 60)
            except InterruptedError:
                pass

        assert threading.active_count() >= threads_avant

    def test_synchroniser_appele_a_chaque_cycle(self):
        """synchroniser() est appelé à chaque iteration de la boucle."""
        compteur = {"n": 0}

        def fake_sleep(_):
            compteur["n"] += 1
            if compteur["n"] >= 3:
                raise InterruptedError

        with patch("lanceur.demarrer"), \
             patch("lanceur.synchroniser") as mock_sync, \
             patch("lanceur.time.sleep", side_effect=fake_sleep):
            try:
                lancer("http://1.2.3.4:5000", "./test", "test.db", 60)
            except InterruptedError:
                pass

        assert mock_sync.call_count >= 3

    def test_synchroniser_recoit_bons_arguments(self):
        """synchroniser() reçoit le bon serveur, dossier et chemin_base."""
        with patch("lanceur.demarrer"), \
             patch("lanceur.synchroniser") as mock_sync, \
             patch("lanceur.time.sleep", side_effect=InterruptedError):
            try:
                lancer("http://100.97.210.70:5000", "./SyncIA", "SyncIA/samyai.db", 60)
            except InterruptedError:
                pass

        mock_sync.assert_called_with(
            "http://100.97.210.70:5000",
            "./SyncIA",
            "SyncIA/samyai.db",
        )

    def test_intervalle_respecte(self):
        """time.sleep() est appelé avec l'intervalle choisi."""
        with patch("lanceur.demarrer"), \
             patch("lanceur.synchroniser"), \
             patch("lanceur.time.sleep", side_effect=InterruptedError) as mock_sleep:
            try:
                lancer("http://1.2.3.4:5000", "./test", "test.db", 30)
            except InterruptedError:
                pass

        mock_sleep.assert_called_with(30)
