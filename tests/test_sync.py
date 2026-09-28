import json
import os
import sqlite3
import time
import shutil
from pathlib import Path
from datetime import datetime

from main import calculer_hash
import sync as sync_module
from sync import (
    comparer_fichiers,
    scanner_dossier,
    synchroniser,
    copier_atomique,
    charger_suppressions,
    enregistrer_suppression,
    nettoyer_temporaires,
    FICHIER_SUPPRESSIONS,
)


# --- Helper ---

def f(hash_val, date, statut="actif"):
    return {"hash": hash_val, "date_modification": date, "statut": statut}


# ====================================================================
#  comparer_fichiers  (7 tests existants, inchanges)
# ====================================================================

class TestComparerFichiers:

    def test_fichier_absent_localement_telecharge(self):
        actions = comparer_fichiers({}, {"a.txt": f("h1", "2026-01-02")})
        assert "a.txt" in actions["a_telecharger"]

    def test_fichier_absent_distants_envoye(self):
        actions = comparer_fichiers({"a.txt": f("h1", "2026-01-01")}, {})
        assert "a.txt" in actions["a_envoyer"]

    def test_fichiers_identiques_aucune_action(self):
        fichier = f("h1", "2026-01-01")
        actions = comparer_fichiers({"a.txt": fichier}, {"a.txt": fichier})
        assert actions["a_telecharger"] == []
        assert actions["a_envoyer"] == []

    def test_distant_plus_recent_telecharge(self):
        actions = comparer_fichiers(
            {"a.txt": f("h1", "2026-01-01")},
            {"a.txt": f("h2", "2026-01-02")},
        )
        assert "a.txt" in actions["a_telecharger"]

    def test_local_plus_recent_envoye(self):
        actions = comparer_fichiers(
            {"a.txt": f("h2", "2026-01-02")},
            {"a.txt": f("h1", "2026-01-01")},
        )
        assert "a.txt" in actions["a_envoyer"]

    def test_meme_date_hash_different_local_gagne(self):
        actions = comparer_fichiers(
            {"a.txt": f("hash_a", "2026-01-01")},
            {"a.txt": f("hash_b", "2026-01-01")},
        )
        assert "a.txt" in actions["a_envoyer"]
        assert actions["conflits"] == []

    def test_fichier_supprime_localement_telecharge(self):
        actions = comparer_fichiers(
            {"a.txt": f("h1", "2026-01-01", statut="supprime")},
            {"a.txt": f("h1", "2026-01-01")},
        )
        assert "a.txt" in actions["a_telecharger"]


# ====================================================================
#  scanner_dossier
# ====================================================================

class TestScannerDossier:

    def test_scanner_dossier_trouve_fichiers(self, tmp_path):
        (tmp_path / "a.txt").write_text("bonjour")
        (tmp_path / "b.pdf").write_bytes(b"\x00pdf")
        (tmp_path / "c.py").write_text("print('hello')")

        resultat = scanner_dossier(str(tmp_path))

        assert "a.txt" in resultat
        assert "b.pdf" in resultat
        assert "c.py" in resultat
        assert len(resultat) == 3

        # Chaque entree contient les champs attendus
        for chemin_rel, infos in resultat.items():
            assert "chemin" in infos
            assert "hash" in infos
            assert "taille" in infos
            assert "date_modification" in infos
            assert "statut" in infos
            assert infos["statut"] == "actif"
            assert len(infos["hash"]) == 64  # SHA-256

    def test_scanner_dossier_ignore_extensions_db(self, tmp_path):
        (tmp_path / "garde.txt").write_text("ok")
        for ext in (".db", ".db-shm", ".db-wal", ".db-journal"):
            (tmp_path / f"ignore{ext}").write_bytes(b"x")

        resultat = scanner_dossier(str(tmp_path))

        assert "garde.txt" in resultat
        assert len(resultat) == 1
        for chemin_rel in resultat:
            assert not chemin_rel.endswith((".db", ".db-shm", ".db-wal", ".db-journal"))

    def test_scanner_dossier_dossier_vide(self, tmp_path):
        resultat = scanner_dossier(str(tmp_path))
        assert resultat == {}

    def test_scanner_dossier_sous_dossiers(self, tmp_path):
        sous = tmp_path / "docs" / "archive"
        sous.mkdir(parents=True)
        (sous / "rapport.txt").write_text("contenu rapport")
        (tmp_path / "racine.txt").write_text("racine")

        resultat = scanner_dossier(str(tmp_path))

        assert "racine.txt" in resultat
        assert "docs/archive/rapport.txt" in resultat
        # Les chemins utilisent des / (posix), pas des \
        for chemin_rel in resultat:
            assert "\\" not in chemin_rel


# ====================================================================
#  synchroniser
# ====================================================================

class TestSynchroniser:

    def _creer_fichier(self, dossier, chemin_relatif, contenu, mtime=None):
        """Cree un fichier dans dossier avec le contenu donne, et optionnellement fixe le mtime."""
        chemin = Path(dossier) / chemin_relatif
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(contenu, encoding="utf-8")
        if mtime is not None:
            os.utime(str(chemin), (mtime, mtime))
        return chemin

    def test_synchroniser_telecharge_fichier_manquant(self, tmp_path):
        """Fichier present sur SMB mais absent en local -> copie vers local."""
        local = tmp_path / "local"
        smb = tmp_path / "smb"
        local.mkdir()
        smb.mkdir()

        self._creer_fichier(smb, "nouveau.txt", "depuis le smb")
        db = str(tmp_path / "test.db")

        synchroniser(str(local), str(smb), chemin_base=db)

        assert (local / "nouveau.txt").exists()
        assert (local / "nouveau.txt").read_text(encoding="utf-8") == "depuis le smb"

    def test_synchroniser_envoie_fichier_manquant(self, tmp_path):
        """Fichier present en local mais absent sur SMB -> copie vers SMB."""
        local = tmp_path / "local"
        smb = tmp_path / "smb"
        local.mkdir()
        smb.mkdir()

        self._creer_fichier(local, "local_only.txt", "fichier local")
        db = str(tmp_path / "test.db")

        synchroniser(str(local), str(smb), chemin_base=db)

        assert (smb / "local_only.txt").exists()
        assert (smb / "local_only.txt").read_text(encoding="utf-8") == "fichier local"

    def test_synchroniser_fichier_plus_recent_gagne(self, tmp_path):
        """Le fichier le plus recent ecrase l'ancien."""
        local = tmp_path / "local"
        smb = tmp_path / "smb"
        local.mkdir()
        smb.mkdir()

        # Le fichier SMB est plus recent
        ancien_ts = datetime(2025, 1, 1).timestamp()
        recent_ts = datetime(2026, 6, 1).timestamp()

        self._creer_fichier(local, "commun.txt", "version ancienne", mtime=ancien_ts)
        self._creer_fichier(smb, "commun.txt", "version recente", mtime=recent_ts)
        db = str(tmp_path / "test.db")

        synchroniser(str(local), str(smb), chemin_base=db)

        # Le contenu local doit etre celui du SMB (plus recent)
        assert (local / "commun.txt").read_text(encoding="utf-8") == "version recente"

    def test_synchroniser_fichiers_identiques_rien_copie(self, tmp_path):
        """Meme contenu des deux cotes -> aucune copie."""
        local = tmp_path / "local"
        smb = tmp_path / "smb"
        local.mkdir()
        smb.mkdir()

        mtime = datetime(2025, 6, 15).timestamp()
        self._creer_fichier(local, "stable.txt", "contenu identique", mtime=mtime)
        self._creer_fichier(smb, "stable.txt", "contenu identique", mtime=mtime)
        db = str(tmp_path / "test.db")

        # Premier scan pour peupler la BDD
        synchroniser(str(local), str(smb), chemin_base=db)

        # Enregistrer le mtime des fichiers apres premiere sync
        mtime_local_avant = os.path.getmtime(str(local / "stable.txt"))
        mtime_smb_avant = os.path.getmtime(str(smb / "stable.txt"))

        # Deuxieme sync : rien ne devrait changer
        synchroniser(str(local), str(smb), chemin_base=db)

        mtime_local_apres = os.path.getmtime(str(local / "stable.txt"))
        mtime_smb_apres = os.path.getmtime(str(smb / "stable.txt"))

        assert mtime_local_avant == mtime_local_apres
        assert mtime_smb_avant == mtime_smb_apres

    def test_synchroniser_smb_inaccessible(self, tmp_path):
        """Dossier SMB inexistant -> pas de crash."""
        local = tmp_path / "local"
        local.mkdir()
        self._creer_fichier(local, "a.txt", "contenu")
        db = str(tmp_path / "test.db")

        smb_inexistant = str(tmp_path / "smb_qui_nexiste_pas")

        # Ne doit pas lever d'exception
        synchroniser(str(local), smb_inexistant, chemin_base=db)

    def test_synchroniser_integrite_hash(self, tmp_path):
        """Apres copie, le hash du fichier source == hash du fichier destination."""
        local = tmp_path / "local"
        smb = tmp_path / "smb"
        local.mkdir()
        smb.mkdir()

        contenu = "donnees importantes a verifier"
        self._creer_fichier(smb, "verif.txt", contenu)
        db = str(tmp_path / "test.db")

        synchroniser(str(local), str(smb), chemin_base=db)

        hash_source = calculer_hash(smb / "verif.txt")
        hash_dest = calculer_hash(local / "verif.txt")
        assert hash_source is not None
        assert hash_dest is not None
        assert hash_source == hash_dest

    def test_synchroniser_preserve_mtime(self, tmp_path):
        """Apres copie via shutil.copy2, le mtime est preserve."""
        local = tmp_path / "local"
        smb = tmp_path / "smb"
        local.mkdir()
        smb.mkdir()

        # Fixer un mtime precis dans le passe
        mtime_original = datetime(2024, 3, 15, 10, 30, 0).timestamp()
        self._creer_fichier(smb, "date.txt", "contenu avec date", mtime=mtime_original)
        db = str(tmp_path / "test.db")

        synchroniser(str(local), str(smb), chemin_base=db)

        assert (local / "date.txt").exists()
        mtime_copie = os.path.getmtime(str(local / "date.txt"))
        # Tolerance de 2 secondes pour les differences de filesystem
        assert abs(mtime_copie - mtime_original) < 2

    def test_synchroniser_suppression_propagee_vers_autre_pc(self, tmp_path):
        """Fichier supprime sur PC-A doit etre supprime du disque local de PC-B."""
        local = tmp_path / "local"
        smb = tmp_path / "smb"
        local.mkdir()
        smb.mkdir()

        mtime = datetime(2025, 1, 1).timestamp()
        self._creer_fichier(local, "a_supprimer.txt", "contenu", mtime=mtime)
        db = str(tmp_path / "test.db")

        # Premier sync : le fichier est envoye sur le SMB
        synchroniser(str(local), str(smb), chemin_base=db)
        assert (smb / "a_supprimer.txt").exists()

        # PC-A enregistre la suppression dans le manifeste (simule la suppression)
        enregistrer_suppression(str(smb), "a_supprimer.txt")
        (smb / "a_supprimer.txt").unlink()

        # Sur PC-B, le fichier est encore en local
        assert (local / "a_supprimer.txt").exists()

        # PC-B synchronise : le fichier local doit etre supprime
        synchroniser(str(local), str(smb), chemin_base=db)

        assert not (local / "a_supprimer.txt").exists()

        # La BDD doit aussi marquer le fichier comme supprime
        connexion = sqlite3.connect(db, timeout=30)
        curseur = connexion.cursor()
        curseur.execute("SELECT statut FROM fichiers WHERE chemin = ?", ("a_supprimer.txt",))
        row = curseur.fetchone()
        connexion.close()
        assert row is not None
        assert row[0] == "supprime"

    def test_synchroniser_cache_smb_reutilise(self, tmp_path):
        """Le cache SMB est reutilise entre les appels a synchroniser."""
        local = tmp_path / "local"
        smb = tmp_path / "smb"
        local.mkdir()
        smb.mkdir()

        self._creer_fichier(smb, "stable.txt", "contenu stable")
        db = str(tmp_path / "test.db")

        # Reset le cache
        sync_module._cache_smb = {}

        synchroniser(str(local), str(smb), chemin_base=db)

        # Le cache doit maintenant contenir les fichiers SMB
        assert "stable.txt" in sync_module._cache_smb
        assert sync_module._cache_smb["stable.txt"]["hash"] is not None


# ====================================================================
#  copier_atomique
# ====================================================================

class TestCopierAtomique:

    def test_copie_reussie(self, tmp_path):
        src = tmp_path / "source.txt"
        src.write_text("contenu original", encoding="utf-8")
        dest = tmp_path / "destination.txt"

        resultat = copier_atomique(src, dest)

        assert resultat is True
        assert dest.exists()
        assert dest.read_text(encoding="utf-8") == "contenu original"

    def test_hash_integrite_apres_copie(self, tmp_path):
        src = tmp_path / "source.txt"
        src.write_bytes(b"donnees binaires \x00\x01\x02\xff")
        dest = tmp_path / "dest.txt"

        copier_atomique(src, dest)

        assert calculer_hash(src) == calculer_hash(dest)

    def test_cree_dossier_parent(self, tmp_path):
        src = tmp_path / "source.txt"
        src.write_text("contenu")
        dest = tmp_path / "sous" / "dossier" / "profond" / "dest.txt"

        resultat = copier_atomique(src, dest)

        assert resultat is True
        assert dest.exists()

    def test_pas_de_fichier_tmp_apres_succes(self, tmp_path):
        src = tmp_path / "source.txt"
        src.write_text("contenu")
        dest = tmp_path / "dest.txt"

        copier_atomique(src, dest)

        # Aucun .syncmate_tmp ne doit rester
        tmp_files = list(tmp_path.glob("*.syncmate_tmp"))
        assert tmp_files == []

    def test_fichier_vide(self, tmp_path):
        src = tmp_path / "vide.txt"
        src.write_bytes(b"")
        dest = tmp_path / "dest_vide.txt"

        resultat = copier_atomique(src, dest)

        assert resultat is True
        assert dest.exists()
        assert dest.stat().st_size == 0

    def test_fichier_avec_accents(self, tmp_path):
        src = tmp_path / "resume_ete_cafe.txt"
        src.write_text("Cafe a la creme", encoding="utf-8")
        dest = tmp_path / "copie_resume_ete_cafe.txt"

        resultat = copier_atomique(src, dest)

        assert resultat is True
        assert dest.read_text(encoding="utf-8") == "Cafe a la creme"

    def test_preserve_mtime(self, tmp_path):
        src = tmp_path / "source.txt"
        src.write_text("contenu")
        mtime_original = datetime(2024, 1, 15, 10, 0, 0).timestamp()
        os.utime(str(src), (mtime_original, mtime_original))
        dest = tmp_path / "dest.txt"

        copier_atomique(src, dest)

        mtime_copie = dest.stat().st_mtime
        assert abs(mtime_copie - mtime_original) < 2

    def test_chemin_long(self, tmp_path):
        # Creer un chemin > 200 caracteres
        sous_dossier = tmp_path / ("a" * 50) / ("b" * 50) / ("c" * 50)
        sous_dossier.mkdir(parents=True, exist_ok=True)
        src = tmp_path / "source.txt"
        src.write_text("chemin long")
        dest = sous_dossier / ("fichier_" + "x" * 50 + ".txt")

        resultat = copier_atomique(src, dest)

        assert resultat is True
        assert dest.read_text(encoding="utf-8") == "chemin long"


# ====================================================================
#  charger_suppressions
# ====================================================================

class TestChargerSuppressions:

    def test_fichier_inexistant_retourne_vide(self, tmp_path):
        resultat = charger_suppressions(str(tmp_path))
        assert resultat == {}

    def test_fichier_json_valide(self, tmp_path):
        donnees = {"doc.txt": {"date": "2026-01-01T00:00:00"}}
        (tmp_path / FICHIER_SUPPRESSIONS).write_text(
            json.dumps(donnees), encoding="utf-8"
        )

        resultat = charger_suppressions(str(tmp_path))

        assert resultat == donnees

    def test_json_corrompu_retourne_vide(self, tmp_path):
        (tmp_path / FICHIER_SUPPRESSIONS).write_text(
            "{{pas du json valide!!", encoding="utf-8"
        )

        resultat = charger_suppressions(str(tmp_path))

        assert resultat == {}

    def test_fichier_vide_retourne_vide(self, tmp_path):
        (tmp_path / FICHIER_SUPPRESSIONS).write_bytes(b"")

        resultat = charger_suppressions(str(tmp_path))

        assert resultat == {}

    def test_chemin_avec_accents(self, tmp_path):
        donnees = {"resume_ete.txt": {"date": "2026-06-01T00:00:00"}}
        (tmp_path / FICHIER_SUPPRESSIONS).write_text(
            json.dumps(donnees, ensure_ascii=False), encoding="utf-8"
        )

        resultat = charger_suppressions(str(tmp_path))

        assert "resume_ete.txt" in resultat


# ====================================================================
#  enregistrer_suppression
# ====================================================================

class TestEnregistrerSuppression:

    def test_enregistre_nouvelle_suppression(self, tmp_path):
        enregistrer_suppression(str(tmp_path), "fichier.txt")

        suppressions = charger_suppressions(str(tmp_path))
        assert "fichier.txt" in suppressions
        assert "date" in suppressions["fichier.txt"]

    def test_ajoute_a_existant(self, tmp_path):
        donnees = {"ancien.txt": {"date": "2026-01-01T00:00:00"}}
        (tmp_path / FICHIER_SUPPRESSIONS).write_text(
            json.dumps(donnees), encoding="utf-8"
        )

        enregistrer_suppression(str(tmp_path), "nouveau.txt")

        suppressions = charger_suppressions(str(tmp_path))
        assert "ancien.txt" in suppressions
        assert "nouveau.txt" in suppressions

    def test_chemin_avec_accents_dans_cle(self, tmp_path):
        enregistrer_suppression(str(tmp_path), "cafe/resume.txt")

        suppressions = charger_suppressions(str(tmp_path))
        assert "cafe/resume.txt" in suppressions

    def test_ecrase_suppression_existante(self, tmp_path):
        enregistrer_suppression(str(tmp_path), "fichier.txt")
        date1 = charger_suppressions(str(tmp_path))["fichier.txt"]["date"]

        time.sleep(0.01)
        enregistrer_suppression(str(tmp_path), "fichier.txt")
        date2 = charger_suppressions(str(tmp_path))["fichier.txt"]["date"]

        assert date2 >= date1

    def test_pas_de_fichier_tmp_residuel(self, tmp_path):
        enregistrer_suppression(str(tmp_path), "fichier.txt")

        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []


# ====================================================================
#  nettoyer_temporaires
# ====================================================================

class TestNettoyerTemporaires:

    def test_supprime_anciens_tmp(self, tmp_path):
        ancien = tmp_path / "vieux.syncmate_tmp"
        ancien.write_text("ancien")
        # Fixer mtime a 2h dans le passe
        vieux_mtime = time.time() - 7200
        os.utime(str(ancien), (vieux_mtime, vieux_mtime))

        nettoyer_temporaires(str(tmp_path))

        assert not ancien.exists()

    def test_garde_recents_tmp(self, tmp_path):
        recent = tmp_path / "recent.syncmate_tmp"
        recent.write_text("recent")
        # Le fichier vient d'etre cree, donc < 1h

        nettoyer_temporaires(str(tmp_path))

        assert recent.exists()

    def test_dossier_vide(self, tmp_path):
        # Ne doit pas lever d'exception
        nettoyer_temporaires(str(tmp_path))

    def test_tmp_dans_sous_dossiers(self, tmp_path):
        sous = tmp_path / "sous" / "dossier"
        sous.mkdir(parents=True)
        ancien = sous / "profond.syncmate_tmp"
        ancien.write_text("ancien")
        vieux_mtime = time.time() - 7200
        os.utime(str(ancien), (vieux_mtime, vieux_mtime))

        nettoyer_temporaires(str(tmp_path))

        assert not ancien.exists()

    def test_ne_touche_pas_vrais_fichiers(self, tmp_path):
        vrai = tmp_path / "document.txt"
        vrai.write_text("important")
        vieux_mtime = time.time() - 7200
        os.utime(str(vrai), (vieux_mtime, vieux_mtime))

        nettoyer_temporaires(str(tmp_path))

        assert vrai.exists()

    def test_melange_anciens_et_recents(self, tmp_path):
        ancien = tmp_path / "vieux.syncmate_tmp"
        ancien.write_text("ancien")
        vieux_mtime = time.time() - 7200
        os.utime(str(ancien), (vieux_mtime, vieux_mtime))

        recent = tmp_path / "nouveau.syncmate_tmp"
        recent.write_text("recent")

        nettoyer_temporaires(str(tmp_path))

        assert not ancien.exists()
        assert recent.exists()


# ====================================================================
#  scanner_dossier avec reference (cache de hash)
# ====================================================================

class TestScannerDossierReference:

    def test_reference_reutilise_hash_si_taille_et_date_identiques(self, tmp_path):
        fichier = tmp_path / "stable.txt"
        fichier.write_text("contenu stable")

        # Premier scan sans reference
        scan1 = scanner_dossier(str(tmp_path))
        hash_original = scan1["stable.txt"]["hash"]

        # Deuxieme scan avec reference = scan1
        # Le hash doit etre reutilise (pas recalcule)
        scan2 = scanner_dossier(str(tmp_path), reference=scan1)

        assert scan2["stable.txt"]["hash"] == hash_original

    def test_reference_recalcule_si_taille_change(self, tmp_path):
        fichier = tmp_path / "modifie.txt"
        fichier.write_text("court")

        scan1 = scanner_dossier(str(tmp_path))
        hash1 = scan1["modifie.txt"]["hash"]

        # Modifier le fichier (change la taille)
        fichier.write_text("contenu beaucoup plus long maintenant")

        scan2 = scanner_dossier(str(tmp_path), reference=scan1)
        hash2 = scan2["modifie.txt"]["hash"]

        assert hash2 != hash1

    def test_reference_vide_recalcule_tout(self, tmp_path):
        (tmp_path / "a.txt").write_text("aaa")

        scan = scanner_dossier(str(tmp_path), reference={})

        assert "a.txt" in scan
        assert len(scan["a.txt"]["hash"]) == 64

    def test_reference_none_recalcule_tout(self, tmp_path):
        (tmp_path / "a.txt").write_text("aaa")

        scan = scanner_dossier(str(tmp_path), reference=None)

        assert "a.txt" in scan
        assert len(scan["a.txt"]["hash"]) == 64


# ====================================================================
#  Edge cases — scanner_dossier
# ====================================================================

class TestScannerDossierEdgeCases:

    def test_fichier_avec_accents(self, tmp_path):
        (tmp_path / "resume.txt").write_text("contenu avec accents eaiu", encoding="utf-8")
        (tmp_path / "cafe_creme.txt").write_text("cafe", encoding="utf-8")

        resultat = scanner_dossier(str(tmp_path))

        assert "resume.txt" in resultat
        assert "cafe_creme.txt" in resultat

    def test_fichier_vide(self, tmp_path):
        (tmp_path / "vide.txt").write_bytes(b"")

        resultat = scanner_dossier(str(tmp_path))

        assert "vide.txt" in resultat
        assert resultat["vide.txt"]["taille"] == 0
        assert len(resultat["vide.txt"]["hash"]) == 64

    def test_ignore_syncmate_tmp(self, tmp_path):
        (tmp_path / "normal.txt").write_text("ok")
        (tmp_path / "copie.txt.syncmate_tmp").write_text("temporaire")

        resultat = scanner_dossier(str(tmp_path))

        assert "normal.txt" in resultat
        assert len(resultat) == 1

    def test_ignore_fichier_suppressions(self, tmp_path):
        (tmp_path / "normal.txt").write_text("ok")
        (tmp_path / FICHIER_SUPPRESSIONS).write_text("{}")

        resultat = scanner_dossier(str(tmp_path))

        assert "normal.txt" in resultat
        assert FICHIER_SUPPRESSIONS not in resultat

    def test_chemin_long(self, tmp_path):
        # Creer un chemin avec nom de dossier/fichier long
        sous = tmp_path / ("dossier_" + "a" * 40)
        sous.mkdir()
        nom_long = "fichier_" + "b" * 40 + ".txt"
        (sous / nom_long).write_text("chemin long")

        resultat = scanner_dossier(str(tmp_path))

        chemin_attendu = ("dossier_" + "a" * 40) + "/" + nom_long
        assert chemin_attendu in resultat
