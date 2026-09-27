from pathlib import Path
from datetime import datetime
import hashlib
import sqlite3
from database import creer_base, NOM_BASE


def calculer_hash(fichier):
    """Calcule le SHA-256 d'un fichier, lu par blocs pour rester léger en mémoire."""
    h = hashlib.sha256()
    try:
        with open(fichier, "rb") as f:
            while morceau := f.read(4096):
                h.update(morceau)
        return h.hexdigest()
    except FileNotFoundError:
        return None


def comparer_etat(ancien, taille_actuelle, hash_actuel):
    """Détermine l'état d'un fichier par rapport à ce qui est enregistré en base.

    ancien : tuple (taille, hash, statut) renvoyé par la BDD, ou None si le fichier
             n'existe pas encore en base.
    Retourne "nouveau", "modifie" ou "inchange".

    La détection de "conflit" nécessite de comparer l'état de deux appareils entre eux
    (PC vs Android) : elle arrivera avec la synchronisation réseau, pas à cette étape.
    """
    if ancien is None:
        return "nouveau"

    ancienne_taille, ancien_hash, ancien_statut = ancien

    # Un fichier qui réapparaît après avoir été marqué supprimé doit être re-synchronisé,
    # même si son contenu est identique à ce qu'il était avant sa suppression.
    if ancien_statut == "supprime":
        return "nouveau"

    if ancienne_taille == taille_actuelle and ancien_hash == hash_actuel:
        return "inchange"

    return "modifie"


def scanner_et_synchroniser_bdd(dossier, chemin_base=NOM_BASE, appareil="PC"):
    """Scanne `dossier` et met à jour la BDD uniquement pour les fichiers nouveaux,
    modifiés ou supprimés. Renvoie la liste des changements détectés."""
    creer_base(chemin_base)

    connexion = sqlite3.connect(chemin_base, timeout=30)
    connexion.execute("PRAGMA journal_mode=WAL")
    curseur = connexion.cursor()
    racine = Path(dossier)
    fichiers_actuels = set()
    changements_detectes = []

    EXTENSIONS_IGNOREES = {".db", ".db-shm", ".db-wal", ".db-journal"}

    for fichier in racine.rglob("*"):
        if not fichier.is_file():
            continue
        if fichier.suffix in EXTENSIONS_IGNOREES:
            continue

        chemin_relatif = str(fichier.relative_to(racine))
        fichiers_actuels.add(chemin_relatif)

        stats = fichier.stat()
        taille = stats.st_size
        date_modification = datetime.fromtimestamp(stats.st_mtime).isoformat(timespec="microseconds")
        extension = fichier.suffix.lstrip(".").lower()

        curseur.execute(
            "SELECT taille, hash, statut, date_modification FROM fichiers WHERE chemin = ?",
            (chemin_relatif,),
        )
        ancien = curseur.fetchone()

        # On recalcule le hash uniquement si la taille OU la date de modification a changé.
        # Vérifier les deux évite de rater une modification où le contenu change
        # mais la taille reste identique (ex : "abc" remplacé par "xyz").
        if ancien is None or ancien[0] != taille or ancien[3] != date_modification:
            hash_actuel = calculer_hash(fichier)
        else:
            hash_actuel = ancien[1]

        statut = comparer_etat(ancien[:3] if ancien else None, taille, hash_actuel)

        if statut == "inchange":
            continue

        curseur.execute("""
            INSERT INTO fichiers (nom, chemin, extension, taille, date_modification, hash, appareil, statut, mis_a_jour_le)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(chemin) DO UPDATE SET
                nom = excluded.nom,
                extension = excluded.extension,
                taille = excluded.taille,
                date_modification = excluded.date_modification,
                hash = excluded.hash,
                appareil = excluded.appareil,
                statut = excluded.statut,
                mis_a_jour_le = CURRENT_TIMESTAMP
        """, (fichier.name, chemin_relatif, extension, taille, date_modification, hash_actuel, appareil, statut))

        changements_detectes.append({"action": statut, "chemin": chemin_relatif})

    # Détection des suppressions : fichiers marqués actifs en base mais absents du disque.
    # On ne supprime pas la ligne : on la marque "supprime" pour garder l'historique.
    curseur.execute("SELECT chemin FROM fichiers WHERE statut != 'supprime'")
    chemins_actifs_en_bdd = [ligne[0] for ligne in curseur.fetchall()]

    for chemin_bdd in chemins_actifs_en_bdd:
        if chemin_bdd not in fichiers_actuels:
            curseur.execute(
                "UPDATE fichiers SET statut = 'supprime', mis_a_jour_le = CURRENT_TIMESTAMP WHERE chemin = ?",
                (chemin_bdd,),
            )
            changements_detectes.append({"action": "supprime", "chemin": chemin_bdd})

    connexion.commit()
    connexion.close()

    return changements_detectes


if __name__ == "__main__":
    dossier_a_scanner = "./test"
    changements = scanner_et_synchroniser_bdd(dossier_a_scanner)

    print("Scan termine !")
    if changements:
        print(f"{len(changements)} changement(s) synchronise(s) dans la BDD locale.")
        for c in changements:
            print(f"  - [{c['action'].upper()}] {c['chemin']}")
    else:
        print("Aucun changement detecte, tout est deja synchronise.")
