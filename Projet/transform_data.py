import pandas as pd
from geopy.distance import geodesic
import os
import sys

# --- Fonctions utilitaires ---

def generate_polyline(flight_df):
    flight_df = flight_df.sort_values("timestamp")
    lat0, long0 = flight_df.iloc[0]["latitude"], flight_df.iloc[0]["longitude"]
    latN, longN = flight_df.iloc[-1]["latitude"], flight_df.iloc[-1]["longitude"]
    
    if len(flight_df) > 2:
        mid_idx = len(flight_df) // 2
        mid_lat, mid_long = flight_df.iloc[mid_idx]["latitude"], flight_df.iloc[mid_idx]["longitude"]
        return f"{lat0},{long0};{mid_lat},{mid_long};{latN},{longN}"
    else:
        return f"{lat0},{long0};{latN},{longN}"

def decode_polyline(polyline):
    if not isinstance(polyline, str): return []
    try:
        pts = polyline.split(';')
        return [tuple(map(float, p.split(','))) for p in pts]
    except:
        return []

def compute_deviation(row):
    real_point = (row["latitude"], row["longitude"])
    route_pts = row["route_points"]
    if not isinstance(route_pts, list) or len(route_pts) == 0: return 0
    try:
        return min(geodesic(real_point, p).meters for p in route_pts)
    except:
        return 0

def generate_autopilot(flight_df):
    n = len(flight_df)
    autopilot = []
    flight_df = flight_df.reset_index(drop=True)
    
    for i in range(n):
        if "anomaly_type" in flight_df.columns and flight_df.loc[i, "anomaly_type"] != "Normal":
            autopilot.append(0)
            continue
        if i < n * 0.10 or i > n * 0.90:
            autopilot.append(0)
            continue
        autopilot.append(1)
    return autopilot

def in_restricted(lat, lon):
    """
    Vérifie si une coordonnée (lat, lon) se trouve dans une zone restreinte.
    Retourne 1 si dans une zone, 0 sinon.
    """
    # Liste des zones restreintes (Format: [Sud-Ouest, Nord-Ouest, Nord-Est, Sud-Est])
    zones = [
        # Paris (Approximatif)
        [(48.5, 2.2), (48.9, 2.2), (48.9, 2.6), (48.5, 2.6)],
        # BA 105 Évreux-Fauville
        [(48.98, 1.15), (49.07, 1.15), (49.07, 1.29), (48.98, 1.29)],
        # BA 118 Mont-de-Marsan
        [(43.87, -0.55), (43.96, -0.55), (43.96, -0.45), (43.87, -0.45)],
        # BA 113 Saint-Dizier-Robinson
        [(48.59, 4.85), (48.68, 4.85), (48.68, 4.95), (48.59, 4.95)],
        # BA 133 Nancy-Ochey
        [(48.54, 5.90), (48.63, 5.90), (48.63, 6.02), (48.54, 6.02)],
        # BA 123 Orléans-Bricy
        [(47.95, 1.70), (48.04, 1.70), (48.04, 1.82), (47.95, 1.82)],
        # BA 115 Orange-Caritat
        [(44.10, 4.80), (44.19, 4.80), (44.19, 4.92), (44.10, 4.92)],
        # BA 106 Bordeaux-Mérignac
        [(44.79, -0.76), (44.87, -0.76), (44.87, -0.66), (44.79, -0.66)],
        # BA 107 Vélizy-Villacoublay
        [(48.75, 2.18), (48.80, 2.18), (48.80, 2.24), (48.75, 2.24)]
    ]

    for zone in zones:
        # On extrait les min/max du rectangle
        lat_min = zone[0][0]
        lat_max = zone[1][0]
        lon_min = zone[0][1]
        lon_max = zone[2][1]
        
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return 1 # True
            
    return 0 # False

def process_flight_data(input_csv_path="test_data_dashboard.csv", output_csv_path="test_data_transformed.csv"):
    #print(f"--- Mode Qualité Stricte ---")
    #print(f"Lecture : {input_csv_path}")
    
    if not os.path.exists(input_csv_path):
        print(f"Erreur : Fichier introuvable.")
        return

    try:
        df_raw = pd.read_csv(input_csv_path)
    except pd.errors.EmptyDataError:
        print("Erreur : Fichier vide.")
        return

    if df_raw.empty:
        print("Erreur : Aucune donnée.")
        return

    # 1. Parsing & Tri
    df_raw["ts_temp"] = pd.to_datetime(
        df_raw["DateGenerated"].astype(str) + " " + df_raw["TimeGenerated"].astype(str), 
        errors='coerce'
    )
    df_raw = df_raw.sort_values(by=["HexIdent", "ts_temp"])

    # 2. DataFrame Initial
    df = pd.DataFrame({
        'flight_id': df_raw["HexIdent"],
        'callsign': df_raw["Callsign"],
        'latitude': pd.to_numeric(df_raw["Latitude"], errors='coerce'),
        'longitude': pd.to_numeric(df_raw["Longitude"], errors='coerce'),
        'altitude': pd.to_numeric(df_raw["Altitude"], errors='coerce'),
        'ground_speed': pd.to_numeric(df_raw["GroundSpeed"], errors='coerce'),
        'heading': pd.to_numeric(df_raw["Track"], errors='coerce'),
        'timestamp': df_raw["ts_temp"]
    })

    # 3. Propagation (On essaie de sauver ce qu'on peut)
    #print("Propagation des données...")
    cols_to_fill = ["callsign", "altitude", "ground_speed", "heading"]
    df[cols_to_fill] = df.groupby("flight_id")[cols_to_fill].ffill().bfill()

    # 4. FILTRAGE STRICT (Ton choix)
    # On supprime TOUTE ligne qui a encore un NaN dans une colonne critique
    initial_count = len(df)
    
    required_columns = ["latitude", "longitude", "timestamp", "flight_id", "callsign", "ground_speed", "heading", "timestamp"]
    df = df.dropna(subset=required_columns)
    
    final_count = len(df)
    dropped_count = initial_count - final_count
    
    """
    print(f"Nettoyage strict terminé :")
    print(f" - Avant : {initial_count} lignes")
    print(f" - Après : {final_count} lignes")
    print(f" - Supprimées (données incomplètes) : {dropped_count}")
    df.info()
    """

    if df.empty:
        print("STOP : Le filtrage strict a supprimé toutes les données.")
        return

    # Ajout colonne technique (non soumise au dropna car créée après)
    df["anomaly_type"] = "Normal"

    # 5. Calculs Métier (Sur données propres uniquement)
    print("Génération des métriques...")
    
    routes = df.groupby("flight_id", group_keys=False).apply(generate_polyline, include_groups=False).reset_index()
    routes.columns = ["flight_id", "intended_route_polyline"]
    df = df.merge(routes, on="flight_id", how="left")

    df["route_points"] = df["intended_route_polyline"].apply(decode_polyline)
    df["deviation_m"] = df.apply(compute_deviation, axis=1)

    df["autopilot_on"] = df.groupby("flight_id", group_keys=False).apply(
        lambda g: pd.Series(generate_autopilot(g), index=g.index),
        include_groups=False
    ).reset_index(level=0, drop=True)

    # 6. Détection Zones Restreintes
    print("Vérification des zones restreintes...")
    df["in_restricted_zone"] = df.apply(
        lambda row: in_restricted(row["latitude"], row["longitude"]), axis=1
    )

    # 7. Export
    target_columns = [
        "flight_id", "callsign", 
        "latitude", "longitude", "altitude", 
        "ground_speed", "heading", 
        "autopilot_on", "deviation_m", "in_restricted_zone", 
        "anomaly_type", "timestamp"
    ]
    
    df_final = df[target_columns]
    
    df_final.to_csv(output_csv_path, index=False)
    #print(f"Terminé : {output_csv_path}")
    df_final.info()

if __name__ == "__main__":
    process_flight_data(input_csv_path="raw_data.csv", output_csv_path="flight_data_transformed.csv")