import dash
from dash import dcc, html, Input, Output, dash_table
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from geopy.distance import geodesic

# =============================================================================
# 1. CHARGEMENT ET PRÉPARATION DES DONNÉES
# =============================================================================

try:
    df = pd.read_csv("dataset_trajectoires_anomalies.csv")
    print("Dataset chargé avec succès.")
except FileNotFoundError:
    exit("Erreur : Le fichier 'dataset_trajectoires_anomalies.csv' est introuvable.")

# --- Fonctions utilitaires ---

def generate_polyline(flight_df):
    flight_df = flight_df.sort_values("timestamp")
    lat0, long0 = flight_df.iloc[0]["latitude"], flight_df.iloc[0]["longitude"]
    latN, longN = flight_df.iloc[-1]["latitude"], flight_df.iloc[-1]["longitude"]
    mid_idx = len(flight_df) // 2
    mid_lat, mid_long = flight_df.iloc[mid_idx]["latitude"], flight_df.iloc[mid_idx]["longitude"]
    return f"{lat0},{long0};{mid_lat},{mid_long};{latN},{longN}"

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
    if not isinstance(route_pts, list) or len(route_pts) == 0:
        return 0
    try:
        return min(geodesic(real_point, p).meters for p in route_pts)
    except:
        return 0

def generate_autopilot(flight_df):
    n = len(flight_df)
    autopilot = []
    # On reset l'index pour itérer proprement de 0 à n
    flight_df = flight_df.reset_index(drop=True)
    
    for i in range(n):
        if flight_df.loc[i, "anomaly_type"] in ["Hijacking_Suspected", "Sharp_Turn_Diversion", "Emergency_Descent"]:
            autopilot.append(0)
            continue
        if i < n * 0.10 or i > n * 0.90:
            autopilot.append(0)
            continue
        autopilot.append(1)
    return autopilot

# --- Application des transformations ---
print("Traitement des données en cours...")

# CORRECTION WARNING PANDAS : Ajout de include_groups=False
routes = df.groupby("flight_id", group_keys=False).apply(generate_polyline, include_groups=False).reset_index()
routes.columns = ["flight_id", "intended_route_polyline"]
df = df.merge(routes, on="flight_id", how="left")

df["route_points"] = df["intended_route_polyline"].apply(decode_polyline)

if 'deviation_m' not in df.columns:
    df["deviation_m"] = df.apply(compute_deviation, axis=1)

# CORRECTION WARNING PANDAS : Ajout de include_groups=False
df["autopilot_on"] = df.groupby("flight_id", group_keys=False).apply(
    lambda g: pd.Series(generate_autopilot(g), index=g.index),
    include_groups=False
).reset_index(level=0, drop=True)

print("Données prêtes.")

# =============================================================================
# 2. CONFIGURATION DU DASHBOARD
# =============================================================================

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server

colors = {'background': '#f9f9f9', 'text': '#111111', 'card': '#ffffff'}
flight_options = [{'label': fid, 'value': fid} for fid in df['flight_id'].unique()]

# =============================================================================
# 3. LAYOUT
# =============================================================================

app.layout = html.Div(style={'backgroundColor': colors['background'], 'padding': '20px'}, children=[
    html.H1("Tableau de Bord : Analyse de Trajectoires Aériennes", 
            style={'textAlign': 'center', 'color': colors['text']}),

    html.Div([
        html.Div([
            html.Label("Sélectionnez un vol :"),
            dcc.Dropdown(
                id='flight-dropdown',
                options=flight_options,
                value=df['flight_id'].unique()[0],
                clearable=False
            )
        ], className="four columns"),
        
        html.Div([
            html.H5(id='kpi-anomaly', style={'color': 'red', 'fontWeight': 'bold'}),
            html.P(id='kpi-stats')
        ], className="eight columns", style={'textAlign': 'right', 'paddingTop': '20px'})
    ], className="row", style={'marginBottom': '20px', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '5px'}),

    html.Div([
        html.Div([
            html.H4("Trajectoire du Vol"),
            dcc.Graph(id='map-graph')
        ], className="eight columns", style={'backgroundColor': 'white', 'padding': '10px'}),

        html.Div([
            html.H4("Déviation / Route (m)"),
            dcc.Graph(id='deviation-graph')
        ], className="four columns", style={'backgroundColor': 'white', 'padding': '10px'}),
    ], className="row", style={'marginBottom': '20px'}),

    html.Div([
        html.Div([dcc.Graph(id='altitude-graph')], className="six columns"),
        html.Div([dcc.Graph(id='speed-graph')], className="six columns"),
    ], className="row"),

    html.Div([
        html.H3("Vue d'ensemble du Dataset"),
        html.Div([dcc.Graph(id='anomaly-pie-chart')], className="six columns"),
        html.Div([dcc.Graph(id='altitude-box-plot')], className="six columns"),
    ], className="row", style={'marginTop': '30px', 'backgroundColor': 'white', 'padding': '15px'})
])

# =============================================================================
# 4. CALLBACKS
# =============================================================================

@app.callback(
    [Output('map-graph', 'figure'),
     Output('deviation-graph', 'figure'),
     Output('altitude-graph', 'figure'),
     Output('speed-graph', 'figure'),
     Output('kpi-anomaly', 'children'),
     Output('kpi-stats', 'children')],
    [Input('flight-dropdown', 'value')]
)
def update_flight_view(selected_flight):
    dff = df[df['flight_id'] == selected_flight].sort_values('timestamp')
    
    anomaly_type = dff['anomaly_type'].iloc[0]
    max_alt = dff['altitude'].max()
    avg_speed = dff['ground_speed'].mean()
    kpi_text = f"Anomalie : {anomaly_type}"
    stats_text = f"Alt Max: {max_alt:.0f}m | Vitesse Moy: {avg_speed:.0f} km/h"

    fig_map = px.scatter_mapbox(
        dff, lat="latitude", lon="longitude", color="altitude",
        hover_data=["ground_speed", "heading", "deviation_m"],
        zoom=5, height=400, title=f"Tracé GPS - {selected_flight}"
    )
    fig_map.update_layout(mapbox_style="open-street-map")
    fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0})

    fig_dev = px.area(dff, x='timestamp', y='deviation_m', title="Écart à la route prévue")
    fig_alt = px.line(dff, x='timestamp', y='altitude', title="Profil d'Altitude")
    fig_speed = px.line(dff, x='timestamp', y='ground_speed', title="Vitesse Sol (km/h)")

    return fig_map, fig_dev, fig_alt, fig_speed, kpi_text, stats_text

@app.callback(
    [Output('anomaly-pie-chart', 'figure'),
     Output('altitude-box-plot', 'figure')],
    [Input('flight-dropdown', 'value')]
)
def update_global_stats(_):
    anomaly_counts = df.groupby('flight_id')['anomaly_type'].first().value_counts().reset_index()
    anomaly_counts.columns = ['Type', 'Count']
    fig_pie = px.pie(anomaly_counts, values='Count', names='Type', title="Répartition des Anomalies")
    
    sample_df = df.sample(min(len(df), 5000))
    fig_box = px.box(sample_df, x='anomaly_type', y='altitude', title="Altitude par Anomalie")

    return fig_pie, fig_box

# =============================================================================
# 5. LANCEMENT DU SERVEUR
# =============================================================================

if __name__ == '__main__':
    # CORRECTION : Remplacement de run_server par run
    app.run(debug=True)