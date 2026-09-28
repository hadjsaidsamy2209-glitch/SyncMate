import json
import os
import sys

NOM_CONFIG = "config.json"


def _chemin_config(nom=None):
    if getattr(sys, "frozen", False):
        dossier = os.path.dirname(sys.executable)
    else:
        dossier = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(dossier, nom or NOM_CONFIG)


def charger_config(nom=None):
    chemin = _chemin_config(nom)
    if not os.path.exists(chemin):
        return None
    try:
        with open(chemin, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "dossier" not in data or "dossier_smb" not in data:
            return None
        return data
    except Exception:
        return None


def sauvegarder_config(dossier, dossier_smb, nom=None):
    chemin = _chemin_config(nom)
    data = {"dossier": dossier, "dossier_smb": dossier_smb}
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
