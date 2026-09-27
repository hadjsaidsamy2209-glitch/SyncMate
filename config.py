import json
import os
import sys

NOM_CONFIG = "config.json"


def _chemin_config():
    """Retourne le chemin de config.json à côté de l'exe (ou du script)."""
    if getattr(sys, "frozen", False):
        # On tourne dans un exe PyInstaller
        dossier = os.path.dirname(sys.executable)
    else:
        # On tourne en script Python normal
        dossier = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(dossier, NOM_CONFIG)


def charger_config():
    """Charge la config. Retourne None si elle n'existe pas."""
    chemin = _chemin_config()
    if not os.path.exists(chemin):
        return None
    try:
        with open(chemin, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def sauvegarder_config(dossier, serveur):
    """Sauvegarde serveur + dossier dans config.json à côté de l'exe."""
    chemin = _chemin_config()
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump({"serveur": serveur, "dossier": dossier}, f, indent=2)
