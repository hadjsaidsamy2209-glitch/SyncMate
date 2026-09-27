import subprocess
import json


def obtenir_machines():
    """Appelle 'tailscale status --json' et retourne la liste des machines connectées."""
    try:
        resultat = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True, text=True, timeout=5
        )
        donnees = json.loads(resultat.stdout)
    except Exception:
        return []

    machines = []

    # La machine locale (Self)
    soi = donnees.get("Self", {})
    ips = soi.get("TailscaleIPs", [])
    if ips:
        machines.append({"nom": soi.get("HostName", "moi"), "ip": ips[0]})

    # Les autres machines (Peer)
    for pair in donnees.get("Peer", {}).values():
        ips = pair.get("TailscaleIPs", [])
        if ips:
            machines.append({"nom": pair.get("HostName", "inconnu"), "ip": ips[0]})

    return machines


def choisir_serveur():
    """Affiche la liste des machines Tailscale et demande à l'utilisateur de choisir le serveur."""
    machines = obtenir_machines()

    if not machines:
        print("Tailscale n'est pas actif ou aucune machine trouvee.")
        print("Entrez l'adresse du serveur manuellement (ex: http://100.97.210.70:5000) :")
        return input("> ").strip()

    print("\nMachines disponibles sur Tailscale :")
    for i, m in enumerate(machines, start=1):
        print(f"  [{i}] {m['nom']:<15} ({m['ip']})")

    while True:
        choix = input(f"\nQuelle machine est le serveur ? (1-{len(machines)}) : ").strip()
        if choix.isdigit() and 1 <= int(choix) <= len(machines):
            machine = machines[int(choix) - 1]
            return f"http://{machine['ip']}:5000"
        print("Choix invalide, réessaie.")


def _dossier_defaut():
    from pathlib import Path
    return str(Path.home() / "SyncIA")


def choisir_dossier(defaut=None):
    """Demande à l'utilisateur quel dossier synchroniser."""
    if defaut is None:
        defaut = _dossier_defaut()
    print(f"\nQuel dossier synchroniser ? (Entree = {defaut}) : ", end="")
    saisie = input().strip()
    return saisie if saisie else defaut
