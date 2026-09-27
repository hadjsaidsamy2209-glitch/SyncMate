# SyncMate

Synchronisation de fichiers bidirectionnelle entre PCs via Tailscale.  
Aucun cloud, aucun serveur tiers — juste deux fichiers `.exe` et un réseau VPN privé.

## Fonctionnalités

- **Sync automatique** toutes les 60 secondes
- **Détection automatique** des machines Tailscale au démarrage
- **Résolution de conflits** automatique (version la plus récente gagne)
- **Vérification d'intégrité** SHA-256 après chaque transfert
- **Surveillance en temps réel** du dossier (watchdog)
- **Cross-platform** — Windows, macOS, Linux

## Prérequis

- [Tailscale](https://tailscale.com/) installé sur les deux machines

## Installation

### PC serveur (PC fixe)

1. Télécharge `server.exe`
2. Lance :
```
server.exe --dossier "C:\Users\SAMY\Desktop\SyncIA"
```

### PC client (PC portable)

1. Télécharge `lanceur.exe`
2. Double-clique — il détecte automatiquement les machines Tailscale
3. Choisis le PC serveur dans la liste
4. La configuration est sauvegardée, les prochains lancements sont automatiques

## Démarrage automatique (Windows)

Utilise le Planificateur de tâches ou place un raccourci dans `shell:startup` pour lancer les exes au démarrage sans fenêtre visible.

## Architecture

```
PC fixe (server.exe)        PC portable (lanceur.exe)
       |                            |
  Flask API :5000   <---Tailscale--->  sync toutes les 60s
  SQLite + watcher                     SQLite + watcher
```

## Stack technique

- **Flask** — API REST sur le serveur
- **SQLite** — base de données locale (WAL mode)
- **watchdog** — surveillance du dossier en temps réel
- **Tailscale** — VPN mesh pour la connexion entre machines
- **PyInstaller** — packaging en `.exe` standalone

## Tests

```
python -m pytest
```

## Licence

MIT
