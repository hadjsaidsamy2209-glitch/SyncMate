"""Tests pour tailscale.py"""

import json
from unittest.mock import patch, MagicMock

from tailscale import obtenir_machines, choisir_serveur, choisir_dossier

REPONSE_API = {
    "Self": {
        "HostName": "samy",
        "TailscaleIPs": ["100.91.174.76"],
    },
    "Peer": {
        "nodekey:abc123": {
            "HostName": "samy-1",
            "TailscaleIPs": ["100.97.210.70"],
        }
    },
}


def mock_subprocess(data):
    """Crée un mock de subprocess.run qui retourne data sérialisé en JSON."""
    m = MagicMock()
    m.stdout = json.dumps(data)
    return m


# ---------------------------------------------------------------------------
# obtenir_machines
# ---------------------------------------------------------------------------

class TestObtenir:

    def test_retourne_self_et_peers(self):
        with patch("tailscale.subprocess.run", return_value=mock_subprocess(REPONSE_API)):
            machines = obtenir_machines()
        noms = [m["nom"] for m in machines]
        assert "samy"   in noms
        assert "samy-1" in noms

    def test_retourne_ips_correctes(self):
        with patch("tailscale.subprocess.run", return_value=mock_subprocess(REPONSE_API)):
            machines = obtenir_machines()
        ips = [m["ip"] for m in machines]
        assert "100.91.174.76" in ips
        assert "100.97.210.70" in ips

    def test_tailscale_inactif_retourne_liste_vide(self):
        with patch("tailscale.subprocess.run", side_effect=FileNotFoundError):
            machines = obtenir_machines()
        assert machines == []

    def test_machine_sans_ip_ignoree(self):
        data = {
            "Self": {"HostName": "samy", "TailscaleIPs": []},
            "Peer": {},
        }
        with patch("tailscale.subprocess.run", return_value=mock_subprocess(data)):
            machines = obtenir_machines()
        assert machines == []

    def test_plusieurs_peers(self):
        data = {
            "Self": {"HostName": "samy", "TailscaleIPs": ["100.91.174.76"]},
            "Peer": {
                "nodekey:aaa": {"HostName": "pc-bureau", "TailscaleIPs": ["100.97.210.70"]},
                "nodekey:bbb": {"HostName": "pc-portable2", "TailscaleIPs": ["100.99.1.1"]},
            },
        }
        with patch("tailscale.subprocess.run", return_value=mock_subprocess(data)):
            machines = obtenir_machines()
        assert len(machines) == 3


# ---------------------------------------------------------------------------
# choisir_serveur
# ---------------------------------------------------------------------------

class TestChoisirServeur:

    def test_retourne_url_avec_port(self):
        with patch("tailscale.obtenir_machines", return_value=[
            {"nom": "samy",   "ip": "100.91.174.76"},
            {"nom": "samy-1", "ip": "100.97.210.70"},
        ]):
            with patch("builtins.input", return_value="2"):
                url = choisir_serveur()
        assert url == "http://100.97.210.70:5000"

    def test_fallback_manuel_si_pas_de_machines(self):
        with patch("tailscale.obtenir_machines", return_value=[]):
            with patch("builtins.input", return_value="http://192.168.1.1:5000"):
                url = choisir_serveur()
        assert url == "http://192.168.1.1:5000"

    def test_redemande_si_choix_invalide(self):
        with patch("tailscale.obtenir_machines", return_value=[
            {"nom": "samy-1", "ip": "100.97.210.70"},
        ]):
            # Premier input invalide ("9"), deuxième valide ("1")
            with patch("builtins.input", side_effect=["9", "1"]):
                url = choisir_serveur()
        assert url == "http://100.97.210.70:5000"


# ---------------------------------------------------------------------------
# choisir_dossier
# ---------------------------------------------------------------------------

class TestChoisirDossier:

    def test_entree_vide_retourne_defaut(self):
        with patch("builtins.input", return_value=""):
            dossier = choisir_dossier(defaut="C:\\SyncIA")
        assert dossier == "C:\\SyncIA"

    def test_saisie_personnalisee(self):
        with patch("builtins.input", return_value="D:\\MonDossier"):
            dossier = choisir_dossier()
        assert dossier == "D:\\MonDossier"
