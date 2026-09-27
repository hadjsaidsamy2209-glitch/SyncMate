import json
import subprocess
from pathlib import Path
from unittest import mock
import pytest
from tailscale import obtenir_machines, choisir_dossier, _dossier_defaut


DONNEES_TAILSCALE = {
    "Self": {"HostName": "pc-fixe", "TailscaleIPs": ["100.1.1.1"]},
    "Peer": {
        "abc123": {"HostName": "pc-portable", "TailscaleIPs": ["100.2.2.2"]}
    },
}


def _mock_run(donnees):
    result = mock.MagicMock()
    result.stdout = json.dumps(donnees)
    return result


class TestObtenir_Machines:

    def test_retourne_soi_et_pair(self):
        with mock.patch("tailscale.subprocess.run", return_value=_mock_run(DONNEES_TAILSCALE)):
            machines = obtenir_machines()
        assert len(machines) == 2
        noms = [m["nom"] for m in machines]
        assert "pc-fixe" in noms
        assert "pc-portable" in noms

    def test_ips_correctes(self):
        with mock.patch("tailscale.subprocess.run", return_value=_mock_run(DONNEES_TAILSCALE)):
            machines = obtenir_machines()
        ips = {m["nom"]: m["ip"] for m in machines}
        assert ips["pc-fixe"] == "100.1.1.1"
        assert ips["pc-portable"] == "100.2.2.2"

    def test_tailscale_inactif_retourne_liste_vide(self):
        with mock.patch("tailscale.subprocess.run", side_effect=Exception("not found")):
            assert obtenir_machines() == []

    def test_json_invalide_retourne_liste_vide(self):
        result = mock.MagicMock()
        result.stdout = "pas_du_json"
        with mock.patch("tailscale.subprocess.run", return_value=result):
            assert obtenir_machines() == []

    def test_sans_peers_retourne_soi_seulement(self):
        donnees = {"Self": {"HostName": "solo", "TailscaleIPs": ["100.9.9.9"]}, "Peer": {}}
        with mock.patch("tailscale.subprocess.run", return_value=_mock_run(donnees)):
            machines = obtenir_machines()
        assert len(machines) == 1
        assert machines[0]["ip"] == "100.9.9.9"

    def test_machine_sans_ip_exclue(self):
        donnees = {
            "Self": {"HostName": "solo", "TailscaleIPs": ["100.9.9.9"]},
            "Peer": {"x": {"HostName": "sans-ip", "TailscaleIPs": []}},
        }
        with mock.patch("tailscale.subprocess.run", return_value=_mock_run(donnees)):
            machines = obtenir_machines()
        assert all(m["nom"] != "sans-ip" for m in machines)


class TestChoisirDossier:

    def test_entree_vide_retourne_defaut(self):
        with mock.patch("builtins.input", return_value=""):
            result = choisir_dossier(defaut="/mon/dossier")
        assert result == "/mon/dossier"

    def test_entree_personnalisee_retourne_saisie(self):
        with mock.patch("builtins.input", return_value="/custom/path"):
            result = choisir_dossier(defaut="/mon/dossier")
        assert result == "/custom/path"

    def test_defaut_none_utilise_home_syncmate(self):
        attendu = str(Path.home() / "SyncMate")
        with mock.patch("builtins.input", return_value=""):
            result = choisir_dossier()
        assert result == attendu
