import subprocess
import json
from pathlib import Path


def obtenir_machines():
    try:
        resultat = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True, text=True, timeout=5
        )
        donnees = json.loads(resultat.stdout)
    except Exception:
        return []

    machines = []

    soi = donnees.get("Self", {})
    ips = soi.get("TailscaleIPs", [])
    if ips:
        machines.append({"nom": soi.get("HostName", "moi"), "ip": ips[0]})

    for pair in donnees.get("Peer", {}).values():
        ips = pair.get("TailscaleIPs", [])
        if ips:
            machines.append({"nom": pair.get("HostName", "inconnu"), "ip": ips[0]})

    return machines


def choisir_serveur():
    machines = obtenir_machines()

    if not machines:
        print("Tailscale inactif. Entrez l'adresse du serveur (ex: http://100.x.x.x:5000) :")
        return input("> ").strip()

    print("\nMachines disponibles :")
    for i, m in enumerate(machines, start=1):
        print(f"  [{i}] {m['nom']:<15} ({m['ip']})")

    while True:
        choix = input(f"\nQuelle machine est le serveur ? (1-{len(machines)}) : ").strip()
        if choix.isdigit() and 1 <= int(choix) <= len(machines):
            machine = machines[int(choix) - 1]
            return f"http://{machine['ip']}:5000"
        print("Choix invalide.")


def _dossier_defaut():
    return str(Path.home() / "SyncMate")


def choisir_dossier(defaut=None):
    if defaut is None:
        defaut = _dossier_defaut()
    print(f"\nDossier a synchroniser (Entree = {defaut}) : ", end="")
    saisie = input().strip()
    return saisie if saisie else defaut
