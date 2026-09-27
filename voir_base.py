import sqlite3

connexion = sqlite3.connect("samyai.db")

curseur = connexion.cursor()

curseur.execute("SELECT * FROM fichiers")

resultat = curseur.fetchall()

for fichier in resultat:
    print(fichier)

connexion.close()