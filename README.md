# SyncMate

Synchronisation de fichiers bidirectionnelle entre machines via Tailscale.  
Aucun cloud, aucun serveur tiers — entièrement privé, fonctionne partout dans le monde.

## Fonctionnalités

- **Sync automatique** toutes les 60 secondes
- **Détection automatique** des machines Tailscale au démarrage
- **Résolution de conflits** automatique (version la plus récente gagne)
- **Vérification d'intégrité** SHA-256 après chaque transfert
- **Surveillance en temps réel** du dossier (watchdog)
- **Configuration persistante** — répond aux questions une seule fois
- **Cross-platform** — Windows, macOS, Linux

## Prérequis

- [Tailscale](https://tailscale.com/) installé sur toutes les machines

## Installation

### Machine serveur

Télécharge `server.exe` et lance :

```
server.exe --dossier "/chemin/vers/le/dossier"
```

### Machine cliente

Télécharge `lanceur.exe` et lance-le. Au premier démarrage :

1. Il affiche la liste des machines connectées sur ton réseau Tailscale
2. Tu choisis quelle machine est le serveur
3. Tu choisis le dossier à synchroniser
4. La configuration est sauvegardée — les prochains lancements sont entièrement automatiques

## Architecture

```
Machine A (server.exe)         Machine B (lanceur.exe)
        |                               |
   Flask API :5000  <---Tailscale--->   sync toutes les 60s
   SQLite + watcher                     SQLite + watcher
```

Plusieurs machines clientes peuvent se connecter au même serveur.

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
