import sqlite3

NOM_BASE = "samyai.db"


def creer_base(chemin_base=NOM_BASE):
    connexion = sqlite3.connect(chemin_base, timeout=30)
    connexion.execute("PRAGMA journal_mode=WAL")
    curseur = connexion.cursor()
    curseur.execute("""
    CREATE TABLE IF NOT EXISTS fichiers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        chemin TEXT NOT NULL UNIQUE,
        extension TEXT,
        taille INTEGER NOT NULL,
        date_modification TIMESTAMP,
        hash TEXT,
        appareil TEXT NOT NULL DEFAULT 'PC',
        statut TEXT NOT NULL DEFAULT 'nouveau',
        mis_a_jour_le TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        derniere_sync_le TIMESTAMP
    )
    """)
    connexion.commit()
    connexion.close()
