import os
import tempfile
import sqlite3
from pathlib import Path
from main import calculer_hash, comparer_etat, scanner_et_synchroniser_bdd


class TestCalculerHash:

    def test_hash_sha256_retourne(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_bytes(b"hello")
        h = calculer_hash(f)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_meme_contenu_meme_hash(self, tmp_path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_bytes(b"syncmate")
        b.write_bytes(b"syncmate")
        assert calculer_hash(a) == calculer_hash(b)

    def test_contenu_different_hash_different(self, tmp_path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_bytes(b"aaa")
        b.write_bytes(b"bbb")
        assert calculer_hash(a) != calculer_hash(b)

    def test_fichier_absent_retourne_none(self, tmp_path):
        assert calculer_hash(tmp_path / "inexistant.txt") is None


class TestComparerEtat:

    def test_ancien_none_est_nouveau(self):
        assert comparer_etat(None, 100, "h1") == "nouveau"

    def test_statut_supprime_est_nouveau(self):
        assert comparer_etat((100, "h1", "supprime"), 100, "h1") == "nouveau"

    def test_taille_et_hash_identiques_inchange(self):
        assert comparer_etat((100, "h1", "actif"), 100, "h1") == "inchange"

    def test_hash_different_modifie(self):
        assert comparer_etat((100, "h1", "actif"), 100, "h2") == "modifie"

    def test_taille_differente_modifie(self):
        assert comparer_etat((100, "h1", "actif"), 200, "h1") == "modifie"


class TestScannerEtSynchroniserBdd:

    def test_nouveau_fichier_insere(self, tmp_path):
        (tmp_path / "a.txt").write_text("contenu")
        db = str(tmp_path / "test.db")
        changements = scanner_et_synchroniser_bdd(str(tmp_path), chemin_base=db)
        chemins = [c["chemin"] for c in changements]
        assert any("a.txt" in c for c in chemins)

    def test_fichiers_db_ignores(self, tmp_path):
        for ext in (".db", ".db-shm", ".db-wal", ".db-journal"):
            (tmp_path / f"ignore{ext}").write_bytes(b"x")
        (tmp_path / "garde.txt").write_text("ok")
        db = str(tmp_path / "test.db")
        changements = scanner_et_synchroniser_bdd(str(tmp_path), chemin_base=db)
        chemins = [c["chemin"] for c in changements]
        assert all(not c.endswith((".db", ".db-shm", ".db-wal", ".db-journal")) for c in chemins)

    def test_fichier_supprime_marque(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("avant")
        db = str(tmp_path / "test.db")
        scanner_et_synchroniser_bdd(str(tmp_path), chemin_base=db)
        f.unlink()
        changements = scanner_et_synchroniser_bdd(str(tmp_path), chemin_base=db)
        assert any(c["action"] == "supprime" for c in changements)

    def test_fichier_inchange_aucun_changement(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("stable")
        db = str(tmp_path / "test.db")
        scanner_et_synchroniser_bdd(str(tmp_path), chemin_base=db)
        changements = scanner_et_synchroniser_bdd(str(tmp_path), chemin_base=db)
        assert changements == []
