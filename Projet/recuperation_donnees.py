import socket
import csv
import os
import time
import sys
from dotenv import load_dotenv

def load_data_from_websocket(nb_messages=5000, output_file="test_data_dashboard.csv"):
    """
    Récupère des données ADS-B de manière robuste.
    Gère les reconnexions, les timeouts et évite les boucles infinies.
    """
    
    # Chargement conf
    load_dotenv()
    
    
    PROJECT_ROOT = os.getenv("PROJECT_ROOT")
    HOST = os.getenv("HOST")
    port_value = os.getenv("PORT")
    if port_value is None:
        raise ValueError("La variable d'environnement PORT n'est pas définie.")

    PORT = int(port_value)

    # Configuration Colonnes ADS-B (Format SBS-1 BaseStation)
    cols = [
        "MessageType", "TransmissionType", "SessionID", "AircraftID", "HexIdent", "FlightID",
        "DateGenerated", "TimeGenerated", "DateLogged", "TimeLogged", "Callsign", "Altitude",
        "GroundSpeed", "Track", "Latitude", "Longitude", "VerticalRate", "Squawk", "Alert",
        "Emergency", "SPI", "IsOnGround"
    ]

    # --- Paramètres de robustesse ---
    MAX_RETRIES = 5          # Nombre max d'essais de reconnexion consécutifs
    TIMEOUT_SOCKET = 10.0    # Temps max d'attente d'un message (secondes)
    RETRY_DELAY = 2          # Temps d'attente initial avant reconnexion
    
    messages_count = 0
    consecutive_errors = 0

    print(f"--- Démarrage Acquisition ---")
    print(f"Cible : {HOST}:{PORT}")
    print(f"Objectif : {nb_messages} messages")
    print(f"Fichier : {output_file}")

    # Boucle globale de gestion de la connexion
    while messages_count < nb_messages:
        
        # Si trop d'erreurs, on abandonne pour ne pas bloquer le dashboard
        if consecutive_errors >= MAX_RETRIES:
            print(f"❌ ABANDON : Trop d'erreurs consécutives ({consecutive_errors}).")
            break

        try:
            print(f"🔌 Tentative de connexion ({consecutive_errors + 1}/{MAX_RETRIES})...")
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(TIMEOUT_SOCKET) # Important : Evite le blocage infini
                s.connect((HOST, PORT))
                print("✅ Connecté ! Réception en cours...")
                
                # Réinitialise le compteur d'erreurs une fois connecté avec succès
                consecutive_errors = 0 
                
                # Ouverture fichier en mode Append
                with open(output_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(cols)

                    # Boucle de lecture socket
                    while messages_count < nb_messages:
                        try:
                            # Lecture bloquante avec timeout
                            chunk = s.recv(4096).decode(errors="ignore")
                            
                            # Si chunk vide, c'est que le serveur a fermé la connexion proprement
                            if not chunk:
                                print("⚠️ Le serveur a fermé la connexion (EOF).")
                                break # Sort de la boucle 'while', déclenche la reconnexion

                            lines = chunk.strip().split("\n")
                            valid_batch_count = 0
                            
                            for line in lines:
                                if line.startswith("MSG"):
                                    fields = line.split(",")
                                    # Correction structurelle des champs manquants
                                    if len(fields) < len(cols):
                                        fields += [""] * (len(cols) - len(fields))
                                    
                                    writer.writerow(fields)
                                    valid_batch_count += 1
                            
                            messages_count += valid_batch_count
                            
                            # Feedback utilisateur régulier
                            if messages_count % 100 == 0 and valid_batch_count > 0:
                                sys.stdout.write(f"\r📥 Progression : {messages_count}/{nb_messages}")
                                sys.stdout.flush()

                        except socket.timeout:
                            # Ce n'est pas grave, on boucle juste. Cela permet au script de rester "vivant"
                            # et de vérifier s'il doit s'arrêter ou continuer
                            # print("... (attente données) ...")
                            continue
                            
                        except OSError as e:
                            print(f"\n⚠️ Erreur Flux : {e}")
                            break # Sort pour reconnexion

        except (socket.error, ConnectionRefusedError, TimeoutError) as e:
            consecutive_errors += 1
            print(f"\n❌ Erreur Connexion : {e}")
            print(f"⏳ Attente de {RETRY_DELAY}s avant nouvelle tentative...")
            time.sleep(RETRY_DELAY)
            RETRY_DELAY *= 1.5 # Backoff : On attend de plus en plus longtemps (2s, 3s, 4.5s...)

        except KeyboardInterrupt:
            print("\n🛑 Arrêt manuel demandé.")
            break

    print(f"\n\n--- Fin Acquisition ---")
    print(f"Total récupéré : {messages_count} / {nb_messages}")
    print(f"Données enregistrées dans : {output_file}")

if __name__ == "__main__":
    load_data_from_websocket()
