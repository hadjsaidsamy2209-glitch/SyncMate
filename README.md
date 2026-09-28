# SyncMate

Synchronisation bidirectionnelle de fichiers entre machines Windows via un partage SMB.
Aucun cloud, aucun serveur tiers — entièrement privé.

## Fonctionnement

Un disque dur USB branché sur une box internet (ou un NAS) sert de stockage partagé SMB.
Chaque machine exécute `lanceur.exe` qui synchronise un dossier local avec le partage toutes les 60 secondes.

- À la maison : accès direct via le réseau local
- En déplacement : accès via VPN (ex : WireGuard intégré à la box)

## Fonctionnalités

- **Sync automatique** toutes les 60 secondes
- **Bidirectionnelle** — les modifications vont dans les deux sens
- **Résolution de conflits** — la version la plus récente gagne
- **Vérification d'intégrité** SHA-256 après chaque transfert (copie atomique)
- **Surveillance en temps réel** du dossier local (watchdog)
- **Propagation des suppressions** via un manifeste JSON sur le partage
- **Configuration persistante** — répondre aux questions une seule fois
- **Démarrage automatique** silencieux au boot (VBS dans le dossier Startup)

## Prérequis

- Un partage SMB accessible (ex : disque USB sur une box, NAS, ou PC partagé)
- Pour l'accès distant : un VPN configuré (WireGuard, OpenVPN, etc.)

## Installation

Télécharge `lanceur.exe` et lance-le. Au premier démarrage :

1. Choisis le dossier local à synchroniser (défaut : `%USERPROFILE%\SyncMate`)
2. Indique le chemin SMB du partage (ex : `\\192.168.1.1\MonDisque\SyncMate`)
3. La configuration est sauvegardée et le démarrage automatique est configuré
4. Les prochains lancements sont entièrement automatiques et silencieux

## Architecture

```
PC A                           Stockage SMB                    PC B
(réseau local)                 (disque USB / NAS)              (VPN ou LAN)
    |                               |                               |
lanceur.exe                   Partage SMB                     lanceur.exe
SQLite + watcher          \\adresse\partage\...               SQLite + watcher
    |                               |                               |
    +----------- shutil.copy2 ------+----------- shutil.copy2 ------+
                    toutes les 60 secondes
```

## Stack technique

- **shutil.copy2** — copie de fichiers avec préservation des métadonnées
- **SQLite** — base de données locale par machine (mode WAL)
- **watchdog** — surveillance du dossier en temps réel
- **PyInstaller** — packaging en `.exe` standalone

## Tests

```
python -m pytest tests/
```

## Licence

MIT
