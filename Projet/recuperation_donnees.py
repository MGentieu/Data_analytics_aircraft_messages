import socket
import glob
import csv
import os
from dotenv import load_dotenv
from datetime import datetime

def load_data_from_websocket(nb_messages=5000, output_file="data_dashboard.csv"):

    load_dotenv()  # charge automatiquement le fichier .env

    PROJECT_ROOT = os.getenv("PROJECT_ROOT")
    HOST = os.getenv("HOST")
    port_value = os.getenv("PORT")

    if port_value is None:
        raise ValueError("La variable d'environnement PORT n'est pas définie.")

    PORT = int(port_value)

    print(f"Projet racine : {PROJECT_ROOT} | Hôte : {HOST} | Port : {PORT}\n")


    cols = [
        "MessageType", "TransmissionType", "SessionID", "AircraftID", "HexIdent", "FlightID",
        "DateGenerated", "TimeGenerated", "DateLogged", "TimeLogged", "Callsign", "Altitude",
        "GroundSpeed", "Track", "Latitude", "Longitude", "VerticalRate", "Squawk", "Alert",
        "Emergency", "SPI", "IsOnGround"
    ]

    print(f"Fichier utilisé en mode APPEND : {output_file}")
    print(f"Connexion à {HOST}:{PORT} ...")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print("Connecté ! Réception des messages ADS-B...\n")

        # Vérifie si le fichier existe et n'est pas vide
        file_exists_and_not_empty = os.path.isfile(output_file) and os.path.getsize(output_file) > 0

        # Ouvre en mode append
        with open(output_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=",")

            # Header uniquement si nouveau fichier ou vide
            if not file_exists_and_not_empty:
                writer.writerow(cols)

            try:
                for i in range(nb_messages):
                    data = s.recv(1024).decode(errors="ignore")

                    for line in data.strip().split("\n"):
                        if line.startswith("MSG"):
                            fields = line.split(",")

                            # Complète les colonnes manquantes
                            if len(fields) < len(cols):
                                fields += [""] * (len(cols) - len(fields))

                            writer.writerow(fields)

                    if i % 5000 == 0:
                        print(f"{i} itérations traitées")
                print(nb_messages, " messages reçus et enregistrés.")
            except KeyboardInterrupt:
                print("\nArrêt manuel par l’utilisateur.")
            except Exception as e:
                print("Erreur :", e)

    print(f"\nDonnées ajoutées dans : {output_file}")

if __name__ == "__main__":
    load_data_from_websocket(nb_messages=100, output_file="test_data_dashboard.csv")
