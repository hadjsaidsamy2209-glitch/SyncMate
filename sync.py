import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from database import NOM_BASE
from main import scanner_et_synchroniser_bdd, calculer_hash, EXTENSIONS_IGNOREES

FICHIER_SUPPRESSIONS = "_syncmate_deletions.json"
FICHIERS_SYNCMATE = {FICHIER_SUPPRESSIONS, ".syncmate_lock", ".syncmate_test"}


def _chemin_sur(chemin_relatif, racine):
    dest = (Path(racine) / chemin_relatif).resolve()
    racine_resolue = Path(racine).resolve()
    if not str(dest).startswith(str(racine_resolue) + os.sep) and dest != racine_resolue:
        return None
    if ".." in Path(chemin_relatif).parts:
        return None
    return dest


def notifier(titre, message):
    try:
        if sys.platform == "win32":
            titre_safe = titre.replace("'", "''")
            message_safe = message.replace("'", "''")
            subprocess.Popen(
                ["powershell", "-WindowStyle", "Hidden", "-Command",
                 f"Add-Type -AssemblyName System.Windows.Forms;"
                 f"$n = New-Object System.Windows.Forms.NotifyIcon;"
                 f"$n.Icon = [System.Drawing.SystemIcons]::Information;"
                 f"$n.Visible = $true;"
                 f"$n.ShowBalloonTip(5000, '{titre_safe}', '{message_safe}', 'Info');"
                 f"Start-Sleep -Seconds 6; $n.Dispose()"],
                creationflags=0x08000000,
            )
        elif sys.platform == "darwin":
            titre_safe = titre.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")
            message_safe = message.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")
            subprocess.Popen(
                ["osascript", "-e",
                 f'display notification "{message_safe}" with title "{titre_safe}"'],
            )
        else:
            subprocess.Popen(["notify-send", titre, message])
    except Exception:
        pass


def lire_fichiers_locaux(chemin_base=NOM_BASE):
    connexion = sqlite3.connect(chemin_base, timeout=30)
    connexion.execute("PRAGMA journal_mode=WAL")
    connexion.row_factory = sqlite3.Row
    curseur = connexion.cursor()
    curseur.execute("""
        SELECT chemin, hash, taille, date_modification, statut, appareil
        FROM fichiers
    """)
    fichiers = {ligne["chemin"]: dict(ligne) for ligne in curseur.fetchall()}
    connexion.close()
    return fichiers


def scanner_dossier(dossier, reference=None):
    racine = Path(dossier)
    fichiers = {}

    for fichier in racine.rglob("*"):
        if not fichier.is_file():
            continue
        if fichier.is_symlink():
            continue
        if fichier.suffix in EXTENSIONS_IGNOREES:
            continue
        if fichier.name in FICHIERS_SYNCMATE or fichier.suffix == ".syncmate_tmp":
            continue

        try:
            fichier.resolve().relative_to(racine.resolve())
        except ValueError:
            continue

        chemin_relatif = fichier.relative_to(racine).as_posix()

        try:
            stats = fichier.stat()
        except (OSError, PermissionError):
            continue

        taille = stats.st_size
        date_modification = datetime.fromtimestamp(stats.st_mtime).isoformat(timespec="microseconds")

        ref = reference.get(chemin_relatif) if reference else None
        if ref and ref.get("taille") == taille and ref.get("date_modification") == date_modification:
            hash_fichier = ref["hash"]
        else:
            hash_fichier = calculer_hash(fichier)

        fichiers[chemin_relatif] = {
            "chemin": chemin_relatif,
            "hash": hash_fichier,
            "taille": taille,
            "date_modification": date_modification,
            "statut": "actif",
        }

    return fichiers


def comparer_fichiers(locaux, distants):
    a_telecharger = []
    a_envoyer = []

    for chemin in set(locaux.keys()) | set(distants.keys()):
        local = locaux.get(chemin)
        distant = distants.get(chemin)

        if local is None or local["statut"] == "supprime":
            if distant is not None:
                a_telecharger.append(chemin)
            continue

        if distant is None:
            a_envoyer.append(chemin)
            continue

        if local["hash"] == distant["hash"]:
            continue

        date_locale = local["date_modification"] or ""
        date_distante = distant["date_modification"] or ""

        if date_locale > date_distante:
            a_envoyer.append(chemin)
        elif date_distante > date_locale:
            a_telecharger.append(chemin)
        else:
            a_envoyer.append(chemin)

    return {"a_telecharger": a_telecharger, "a_envoyer": a_envoyer, "conflits": []}


def charger_suppressions(dossier_smb):
    chemin = Path(dossier_smb) / FICHIER_SUPPRESSIONS
    if not chemin.exists():
        return {}
    try:
        with open(chemin, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def enregistrer_suppression(dossier_smb, chemin_relatif):
    suppressions = charger_suppressions(dossier_smb)
    suppressions[chemin_relatif] = {"date": datetime.now().isoformat()}
    chemin = Path(dossier_smb) / FICHIER_SUPPRESSIONS
    tmp = chemin.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(suppressions, f, indent=2, ensure_ascii=False)
        tmp.replace(chemin)
    except OSError:
        tmp.unlink(missing_ok=True)


def copier_atomique(source, destination):
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".syncmate_tmp")
    try:
        shutil.copy2(str(source), str(tmp))
        hash_source = calculer_hash(source)
        hash_copie = calculer_hash(tmp)
        if hash_source != hash_copie:
            tmp.unlink(missing_ok=True)
            return False
        tmp.replace(dest)
        return True
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def nettoyer_temporaires(dossier):
    for tmp in Path(dossier).rglob("*.syncmate_tmp"):
        try:
            age = time.time() - tmp.stat().st_mtime
            if age > 3600:
                tmp.unlink()
        except OSError:
            pass


_cache_smb = {}


def synchroniser(dossier_local, dossier_smb, chemin_base=NOM_BASE):
    global _cache_smb
    import watcher
    watcher.sync_en_cours = True

    try:
        scanner_et_synchroniser_bdd(dossier_local, chemin_base=chemin_base)
        locaux = lire_fichiers_locaux(chemin_base)

        try:
            smb = scanner_dossier(dossier_smb, reference=_cache_smb)
        except OSError as e:
            print(f"Impossible d'acceder au dossier SMB : {e}")
            return
        _cache_smb = smb

        suppressions = charger_suppressions(dossier_smb)
        nettoyer_temporaires(dossier_smb)
        nettoyer_temporaires(dossier_local)

        actions = comparer_fichiers(locaux, smb)

        # Filtrer les uploads : ne pas re-uploader un fichier supprimé par un autre PC
        a_envoyer_filtre = []
        for chemin in actions["a_envoyer"]:
            if chemin in suppressions:
                date_sup = suppressions[chemin].get("date", "")
                date_local = locaux.get(chemin, {}).get("date_modification", "")
                if date_sup > date_local:
                    fichier_local = Path(dossier_local) / chemin
                    try:
                        fichier_local.unlink()
                    except OSError:
                        pass
                    connexion = sqlite3.connect(chemin_base, timeout=30)
                    connexion.execute("PRAGMA journal_mode=WAL")
                    connexion.execute(
                        "UPDATE fichiers SET statut = 'supprime', mis_a_jour_le = CURRENT_TIMESTAMP WHERE chemin = ?",
                        (chemin,),
                    )
                    connexion.commit()
                    connexion.close()
                    continue
            a_envoyer_filtre.append(chemin)
        actions["a_envoyer"] = a_envoyer_filtre

        # Filtrer les downloads : ne pas re-télécharger un fichier supprimé localement
        a_telecharger_filtre = []
        for chemin in actions["a_telecharger"]:
            local = locaux.get(chemin)
            if local and local["statut"] == "supprime":
                enregistrer_suppression(dossier_smb, chemin)
                fichier_smb = Path(dossier_smb) / chemin
                try:
                    fichier_smb.unlink()
                except OSError:
                    pass
                continue
            a_telecharger_filtre.append(chemin)
        actions["a_telecharger"] = a_telecharger_filtre

        total = len(actions["a_telecharger"]) + len(actions["a_envoyer"])
        if total == 0:
            print("Tout est deja synchronise.")
            return

        telecharges = []
        envoyes = []

        if actions["a_telecharger"]:
            print(f"\nFichiers a telecharger ({len(actions['a_telecharger'])}) :")
            for chemin in actions["a_telecharger"]:
                if not _chemin_sur(chemin, dossier_smb) or not _chemin_sur(chemin, dossier_local):
                    print(f"  [BLOQUE] Chemin suspect : {chemin}")
                    continue
                source = Path(dossier_smb) / chemin
                destination = Path(dossier_local) / chemin
                try:
                    if copier_atomique(source, destination):
                        print(f"  [TELECHARGE] {chemin}")
                        telecharges.append(Path(chemin).name)
                    else:
                        print(f"  [AVERTISSEMENT] Copie corrompue : {chemin}")
                except (OSError, PermissionError) as e:
                    print(f"  [ERREUR] {chemin} : {e}")

        if actions["a_envoyer"]:
            print(f"\nFichiers a envoyer ({len(actions['a_envoyer'])}) :")
            for chemin in actions["a_envoyer"]:
                if not _chemin_sur(chemin, dossier_local) or not _chemin_sur(chemin, dossier_smb):
                    print(f"  [BLOQUE] Chemin suspect : {chemin}")
                    continue
                source = Path(dossier_local) / chemin
                destination = Path(dossier_smb) / chemin
                try:
                    if copier_atomique(source, destination):
                        print(f"  [ENVOYE] {chemin}")
                        envoyes.append(Path(chemin).name)
                    else:
                        print(f"  [AVERTISSEMENT] Copie corrompue : {chemin}")
                except (OSError, PermissionError) as e:
                    print(f"  [ERREUR] {chemin} : {e}")

        if telecharges:
            noms = ", ".join(telecharges[:3])
            reste = f" +{len(telecharges) - 3}" if len(telecharges) > 3 else ""
            notifier("Fichiers recus", f"{noms}{reste}")

        if envoyes:
            noms = ", ".join(envoyes[:3])
            reste = f" +{len(envoyes) - 3}" if len(envoyes) > 3 else ""
            notifier("Fichiers envoyes", f"{noms}{reste}")

        print("\nSynchronisation terminee.")

    finally:
        time.sleep(1)
        watcher.sync_en_cours = False
