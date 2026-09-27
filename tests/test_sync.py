from sync import comparer_fichiers


def f(hash_val, date, statut="actif"):
    return {"hash": hash_val, "date_modification": date, "statut": statut}


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
