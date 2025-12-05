import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import os

# =============================================================================
# 1. CHARGEMENT DES DONNÉES TRANSFORMÉES
# =============================================================================

INPUT_FILE = "test_data_transformed.csv"

if not os.path.exists(INPUT_FILE):
    print(f"ERREUR : Le fichier '{INPUT_FILE}' est introuvable.")
    print("Veuillez d'abord exécuter le script 'transform_data.py'.")
    exit()

print(f"Chargement des données depuis {INPUT_FILE}...")
df = pd.read_csv(INPUT_FILE)

# Conversion temporelle essentielle pour l'affichage des graphiques
if 'timestamp' in df.columns:
    df['timestamp'] = pd.to_datetime(df['timestamp'])

# Vérification basique
required_cols = ['flight_id', 'latitude', 'longitude', 'ground_speed', 'altitude']
missing_cols = [c for c in required_cols if c not in df.columns]
if missing_cols:
    print(f"ATTENTION : Colonnes manquantes dans le CSV : {missing_cols}")

print("Données chargées. Démarrage du Dashboard.")

# =============================================================================
# 2. CONFIGURATION DU DASHBOARD
# =============================================================================

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server

colors = {'background': '#f4f6f8', 'text': '#2c3e50', 'card': '#ffffff'}

# Création de la liste des options pour le menu déroulant
# On affiche "Callsign (HexIdent)" pour que ce soit plus lisible
if 'callsign' in df.columns:
    flight_options = [
        {'label': f"{row['callsign']} ({fid})", 'value': fid}
        for fid, row in df.groupby('flight_id').first().iterrows()
    ]
else:
    flight_options = [{'label': fid, 'value': fid} for fid in df['flight_id'].unique()]

# =============================================================================
# 3. LAYOUT (Mise en page)
# =============================================================================

app.layout = html.Div(style={'backgroundColor': colors['background'], 'padding': '20px', 'fontFamily': 'Arial, sans-serif'}, children=[
    
    # --- En-tête ---
    html.H1("Dashboard Analyse de Vols (ADS-B)", 
            style={'textAlign': 'center', 'color': colors['text'], 'marginBottom': '30px'}),

    # --- Barre de Contrôle ---
    html.Div([
        html.Div([
            html.Label("✈️ Sélectionner un vol :", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='flight-dropdown',
                options=flight_options,
                # Sélectionne le premier vol par défaut s'il y en a
                value=flight_options[0]['value'] if flight_options else None,
                clearable=False,
                style={'width': '100%'}
            )
        ], className="four columns"),
        
        html.Div([
            html.H5(id='kpi-status', style={'fontWeight': 'bold', 'marginTop': '0px'}),
            html.Div(id='kpi-details', style={'fontSize': '14px', 'color': '#555'})
        ], className="eight columns", style={'textAlign': 'right', 'borderLeft': '1px solid #ddd'})
    ], className="row", style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),

    html.Br(),

    # --- Ligne 1 : Carte et Déviation ---
    html.Div([
        # Carte
        html.Div([
            html.H5("📍 Trajectoire GPS"),
            dcc.Graph(id='map-graph', style={'height': '400px'})
        ], className="eight columns", style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'marginRight': '1%'}),

        # Déviation
        html.Div([
            html.H5("⚠️ Déviation (m)"),
            dcc.Graph(id='deviation-graph', style={'height': '400px'})
        ], className="four columns", style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px'})
    ], className="row"),

    html.Br(),

    # --- Ligne 2 : Télémétrie (Altitude & Vitesse Sol uniquement) ---
    html.Div([
        html.Div([
            dcc.Graph(id='altitude-graph')
        ], className="six columns", style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'marginRight': '1%'}),

        html.Div([
            dcc.Graph(id='speed-graph')
        ], className="six columns", style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px'}),
    ], className="row"),

    # --- Pied de page : Statistiques Globales ---
    html.Br(),
    html.Div([
        html.H4("Statistiques Globales du Dataset", style={'textAlign': 'center'}),
        html.Div([
            html.Div([dcc.Graph(id='global-pie-chart')], className="six columns"),
            html.Div([dcc.Graph(id='global-box-plot')], className="six columns")
        ], className="row")
    ], style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'marginTop': '20px'})
])

# =============================================================================
# 4. CALLBACKS (Logique)
# =============================================================================

@app.callback(
    [Output('map-graph', 'figure'),
     Output('deviation-graph', 'figure'),
     Output('altitude-graph', 'figure'),
     Output('speed-graph', 'figure'),
     Output('kpi-status', 'children'),
     Output('kpi-status', 'style'),
     Output('kpi-details', 'children')],
    [Input('flight-dropdown', 'value')]
)
def update_flight_view(selected_flight):
    if not selected_flight:
        return {}, {}, {}, {}, "Aucun vol sélectionné", {}, ""

    # Filtrage des données pour le vol choisi
    dff = df[df['flight_id'] == selected_flight].sort_values('timestamp')
    
    if dff.empty:
        return {}, {}, {}, {}, "Données introuvables", {}, ""

    # KPIs
    # On récupère le type d'anomalie (s'il existe, sinon "Normal" par défaut)
    anomaly = dff['anomaly_type'].iloc[0] if 'anomaly_type' in dff.columns else "Normal"
    
    callsign = dff['callsign'].iloc[0] if 'callsign' in dff.columns else "Unknown"
    max_alt = dff['altitude'].max()
    avg_speed = dff['ground_speed'].mean()
    
    status_text = f"Statut : {anomaly}"
    status_style = {'color': 'green', 'fontWeight': 'bold'} if anomaly == "Normal" else {'color': 'red', 'fontWeight': 'bold'}
    
    details_text = f"Callsign: {callsign} | Alt Max: {max_alt:.0f} ft | Vitesse Moy: {avg_speed:.0f} kts"

    # 1. Carte
    fig_map = px.scatter_mapbox(
        dff, lat="latitude", lon="longitude", color="altitude",
        hover_data=["ground_speed", "heading"],
        zoom=5, height=350
    )
    fig_map.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0})

    # 2. Déviation
    if 'deviation_m' in dff.columns:
        fig_dev = px.area(dff, x='timestamp', y='deviation_m', title="Écart à la route théorique")
        fig_dev.update_traces(line_color='#e74c3c')
    else:
        fig_dev = px.line(title="Pas de données de déviation")

    # 3. Altitude
    fig_alt = px.line(dff, x='timestamp', y='altitude', title="Profil d'Altitude (ft)")
    fig_alt.update_traces(line_color='#3498db')

    # 4. Vitesse Sol (Pas de VerticalSpeed ici)
    fig_speed = px.line(dff, x='timestamp', y='ground_speed', title="Vitesse Sol (kts)")
    fig_speed.update_traces(line_color='#f39c12')

    return fig_map, fig_dev, fig_alt, fig_speed, status_text, status_style, details_text


@app.callback(
    [Output('global-pie-chart', 'figure'),
     Output('global-box-plot', 'figure')],
    [Input('flight-dropdown', 'value')] # Dummy input pour déclencher au chargement
)
def update_global_stats(_):
    # Camembert des types de vols
    if 'anomaly_type' in df.columns:
        # On prend une ligne par vol pour compter
        unique_flights = df.groupby('flight_id').first().reset_index()
        counts = unique_flights['anomaly_type'].value_counts().reset_index()
        counts.columns = ['Type', 'Count']
        fig_pie = px.pie(counts, values='Count', names='Type', title="Répartition Normal / Anomalie", hole=0.3)
    else:
        fig_pie = px.pie(title="Données 'anomaly_type' manquantes")

    # Boite à moustache Altitude vs Type
    # On échantillonne pour éviter de faire ramer le navigateur si > 10k points
    if len(df) > 5000:
        sample_df = df.sample(5000)
    else:
        sample_df = df
        
    if 'anomaly_type' in df.columns:
        fig_box = px.box(sample_df, x='anomaly_type', y='altitude', title="Distribution Altitude par Type")
    else:
        fig_box = px.box(sample_df, y='altitude', title="Distribution Altitude Globale")

    return fig_pie, fig_box

# =============================================================================
# 5. MAIN
# =============================================================================

if __name__ == '__main__':
    print("Serveur Dashboard lancé sur http://127.0.0.1:8050/")
    app.run(debug=True)