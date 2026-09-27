import json
import os
import sys
from unittest import mock
import pytest
import config as cfg


class TestCheminConfig:

    def test_chemin_next_to_exe_si_frozen(self, tmp_path):
        exe = str(tmp_path / "lanceur.exe")
        with mock.patch.object(sys, "frozen", True, create=True), \
             mock.patch.object(sys, "executable", exe):
            chemin = cfg._chemin_config()
        assert chemin == str(tmp_path / "config.json")

    def test_chemin_next_to_script_si_pas_frozen(self):
        chemin = cfg._chemin_config()
        assert chemin.endswith("config.json")
        assert os.path.dirname(chemin) == os.path.dirname(os.path.abspath(cfg.__file__))


class TestChargerConfig:

    def test_retourne_none_si_absente(self, tmp_path):
        with mock.patch("config._chemin_config", return_value=str(tmp_path / "config.json")):
            assert cfg.charger_config() is None

    def test_retourne_none_si_json_invalide(self, tmp_path):
        f = tmp_path / "config.json"
        f.write_text("pas_du_json{{{")
        with mock.patch("config._chemin_config", return_value=str(f)):
            assert cfg.charger_config() is None

    def test_retourne_dict_valide(self, tmp_path):
        f = tmp_path / "config.json"
        donnees = {"serveur": "http://100.1.2.3:5000", "dossier": "/data/sync"}
        f.write_text(json.dumps(donnees))
        with mock.patch("config._chemin_config", return_value=str(f)):
            result = cfg.charger_config()
        assert result == donnees


class TestSauvegarderConfig:

    def test_fichier_cree_avec_bonnes_valeurs(self, tmp_path):
        f = tmp_path / "config.json"
        with mock.patch("config._chemin_config", return_value=str(f)):
            cfg.sauvegarder_config("/data/sync", "http://100.1.2.3:5000")
        contenu = json.loads(f.read_text())
        assert contenu["serveur"] == "http://100.1.2.3:5000"
        assert contenu["dossier"] == "/data/sync"

    def test_ecrasement_config_existante(self, tmp_path):
        f = tmp_path / "config.json"
        f.write_text(json.dumps({"serveur": "old", "dossier": "old"}))
        with mock.patch("config._chemin_config", return_value=str(f)):
            cfg.sauvegarder_config("/nouveau", "http://nouveau:5000")
        contenu = json.loads(f.read_text())
        assert contenu["serveur"] == "http://nouveau:5000"
        assert contenu["dossier"] == "/nouveau"
