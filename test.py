import socket
import csv
from datetime import datetime

# Paramètres du serveur Glidernet
HOST = "sbs.glidernet.org"
PORT = 30003

# Fichier CSV de sortie
output_file = f"adsb_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

print(f"Connexion à {HOST}:{PORT} ...")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    print("Connecté ! Réception des messages ADS-B...\n")
    
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Message"])  # Une seule colonne pour l'instant

        try:
            for i in range(500):  # Nombre de messages à lire
                data = s.recv(1024).decode(errors="ignore")
                for line in data.strip().split("\n"):
                    if line.startswith("MSG"):
                        writer.writerow([line])
                        print(line)
        except KeyboardInterrupt:
            print("\nArrêt manuel.")
        except Exception as e:
            print("Erreur :", e)

print(f"\nDonnées enregistrées dans : {output_file}")
