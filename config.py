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
            return json.load(f)
    except Exception:
        return None


def sauvegarder_config(dossier, serveur, nom=None):
    chemin = _chemin_config(nom)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump({"serveur": serveur, "dossier": dossier}, f, indent=2)
