import dash
from dash import dcc, html, Input, Output, State, dash_table
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import os
import time
from datetime import datetime

# Import de vos modules personnalisés
from recuperation_donnees import load_data_from_websocket
from transform_data import process_flight_data
from model import FlightModel

# =============================================================================
# 1. CONSTANTES & CONFIGURATION
# =============================================================================

# Liste des zones restreintes pour affichage (Format: SW, NW, NE, SE)
# Copié depuis transform_data pour la visualisation
RESTRICTED_ZONES = [
    [(48.5, 2.2), (48.9, 2.2), (48.9, 2.6), (48.5, 2.6)], # Paris
    [(48.98, 1.15), (49.07, 1.15), (49.07, 1.29), (48.98, 1.29)], # Evreux
    [(43.87, -0.55), (43.96, -0.55), (43.96, -0.45), (43.87, -0.45)], # Mont-de-Marsan
    [(48.59, 4.85), (48.68, 4.85), (48.68, 4.95), (48.59, 4.95)], # St-Dizier
    [(48.54, 5.90), (48.63, 5.90), (48.63, 6.02), (48.54, 6.02)], # Nancy
    [(47.95, 1.70), (48.04, 1.70), (48.04, 1.82), (47.95, 1.82)], # Orléans
    [(44.10, 4.80), (44.19, 4.80), (44.19, 4.92), (44.10, 4.92)], # Orange
    [(44.79, -0.76), (44.87, -0.76), (44.87, -0.66), (44.79, -0.66)], # Bordeaux
    [(48.75, 2.18), (48.80, 2.18), (48.80, 2.24), (48.75, 2.24)] # Villacoublay
]

# Chargement du modèle
print("--- Initialisation du Dashboard ---")
try:
    ai_pilot = FlightModel()
    ai_pilot.load_model()
    MODEL_LOADED = True
    print("✅ Modèle IA chargé avec succès.")
except Exception as e:
    print(f"⚠️ Attention : Impossible de charger le modèle ({e}). Les prédictions seront indisponibles.")
    MODEL_LOADED = False

# Noms de fichiers
RAW_FILE = "raw_data.csv"
TRANSFORMED_FILE = "flight_data_transformed.csv"

# =============================================================================
# 2. LOGIQUE MÉTIER
# =============================================================================

def load_and_predict_data():
    if not os.path.exists(TRANSFORMED_FILE):
        return pd.DataFrame()

    df = pd.read_csv(TRANSFORMED_FILE)
    
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])

    if MODEL_LOADED and not df.empty:
        try:
            print("Lancement des prédictions IA...")
            df['predicted_anomaly'] = ai_pilot.predict(df)
        except Exception as e:
            print(f"Erreur prédiction : {e}")
            df['predicted_anomaly'] = "Non calculé"
    else:
        df['predicted_anomaly'] = "Modèle non chargé"
    
    return df

global_df = load_and_predict_data()

# =============================================================================
# 3. LAYOUT DASH
# =============================================================================

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server

colors = {
    'background': '#1a1c23',
    'card': '#2c313c',
    'text': '#ffffff',
    'accent': '#3498db',
    'danger': '#e74c3c',
    'success': '#2ecc71',
    'warning': '#f39c12'
}

def create_card(title, value, id_value, color=colors['text']):
    return html.Div([
        html.H6(title, style={'color': '#aaaaaa', 'marginBottom': '5px', 'fontSize': '14px'}),
        html.H2(value, id=id_value, style={'color': color, 'fontWeight': 'bold', 'marginTop': '0px', 'fontSize': '28px'})
    ], style={'backgroundColor': colors['card'], 'padding': '15px', 'borderRadius': '8px', 'textAlign': 'center', 'height': '100%'})

app.layout = html.Div(style={'backgroundColor': colors['background'], 'color': colors['text'], 'minHeight': '100vh', 'padding': '20px', 'fontFamily': 'Segoe UI, sans-serif'}, children=[
    
    # --- HEADER ---
    html.Div([
        html.H1("✈️ ADS-B SENTINEL", style={'float': 'left', 'fontWeight': 'bold', 'letterSpacing': '2px'}),
        html.Div([
            html.Button("🔄 Màj Données", id='btn-update', n_clicks=0, 
                       style={'backgroundColor': colors['accent'], 'color': 'white', 'border': 'none', 'fontSize': '16px', 'padding': '10px 20px', 'cursor': 'pointer', 'borderRadius': '5px'}),
            html.Div(id='last-update-time', style={'marginTop': '5px', 'fontSize': '12px', 'color': '#888', 'textAlign': 'right'})
        ], style={'float': 'right'}),
        html.Div(style={'clear': 'both'})
    ], style={'marginBottom': '30px', 'borderBottom': '1px solid #444', 'paddingBottom': '20px'}),

    dcc.Loading(id="loading-data", type="default", children=html.Div(id="loading-output", style={'display': 'none'})),

    # --- KPIs GLOBAUX (5 cartes) ---
    html.Div([
        # On utilise un style flexbox ou des largeurs en % pour faire tenir 5 cartes
        html.Div(create_card("Vols Suivis", "0", "kpi-total-flights"), style={'width': '18%', 'display': 'inline-block', 'marginRight': '2%'}),
        html.Div(create_card("Alertes IA", "0", "kpi-anomalies", colors['danger']), style={'width': '18%', 'display': 'inline-block', 'marginRight': '2%'}),
        # NOUVELLE MÉTRIQUE
        html.Div(create_card("Intrusions Zones", "0", "kpi-restricted", colors['warning']), style={'width': '18%', 'display': 'inline-block', 'marginRight': '2%'}),
        html.Div(create_card("Taux Anomalie", "0%", "kpi-ratio"), style={'width': '18%', 'display': 'inline-block', 'marginRight': '2%'}),
        html.Div(create_card("Dernier Contact", "-", "kpi-last-contact"), style={'width': '18%', 'display': 'inline-block'}),
    ], style={'marginBottom': '30px', 'display': 'flex', 'justifyContent': 'space-between'}),

    # --- SECTION CRITIQUE ---
    html.H4("⚠️ Top 5 : Vols Critiques (IA & Zones)", style={'color': colors['danger'], 'borderLeft': f"5px solid {colors['danger']}", 'paddingLeft': '10px'}),
    html.Div([
        dash_table.DataTable(
            id='critical-table',
            columns=[
                {"name": "Flight ID", "id": "flight_id"},
                {"name": "Callsign", "id": "callsign"},
                {"name": "Dernière Anomalie", "id": "predicted_anomaly"},
                {"name": "Zone Restreinte ?", "id": "in_restricted_zone"}, # Ajout visuel
                {"name": "Vitesse", "id": "ground_speed"},
                {"name": "Altitude", "id": "altitude"},
                {"name": "Heure (UTC+0)", "id": "timestamp"}
            ],
            style_header={'backgroundColor': '#2c313c', 'color': 'white', 'fontWeight': 'bold', 'border': '1px solid #444'},
            style_cell={'backgroundColor': '#1a1c23', 'color': 'white', 'border': '1px solid #444', 'textAlign': 'left'},
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#23262e'},
                # Mettre en rouge si dans zone restreinte
                {'if': {'filter_query': '{in_restricted_zone} = 1', 'column_id': 'in_restricted_zone'}, 'color': colors['warning'], 'fontWeight': 'bold'}
            ]
        )
    ], style={'marginBottom': '40px'}),

    # --- ANALYSE DÉTAILLÉE ---
    html.Div([
        html.H4("🔎 Analyse Détaillée par Vol", style={'color': colors['accent'], 'borderLeft': f"5px solid {colors['accent']}", 'paddingLeft': '10px'}),
        
        html.Div([
            html.Label("Sélectionner un vol :"),
            dcc.Dropdown(id='flight-dropdown', style={'color': '#000'})
        ], style={'marginBottom': '20px'}),

        html.Div(id='flight-details-panel', style={'padding': '15px', 'backgroundColor': colors['card'], 'borderRadius': '5px', 'marginBottom': '20px'}),

        # Ligne 1 : Carte et Déviation
        html.Div([
            html.Div([dcc.Graph(id='map-graph')], className="eight columns"),
            html.Div([dcc.Graph(id='deviation-graph')], className="four columns"),
        ], className="row"),

        # Ligne 2 : Altitude et Vitesse
        html.Div([
            html.Div([dcc.Graph(id='altitude-graph')], className="six columns"),
            html.Div([dcc.Graph(id='speed-graph')], className="six columns"),
        ], className="row", style={'marginTop': '20px'}),

        # Stats globales
        html.H4("📊 Statistiques Globales", style={'marginTop': '40px', 'borderTop': '1px solid #444', 'paddingTop': '20px'}),
        html.Div([
            html.Div([dcc.Graph(id='pie-chart')], className="six columns"),
            html.Div([dcc.Graph(id='box-plot')], className="six columns"),
        ], className="row")
    ])
])

# =============================================================================
# 4. CALLBACKS
# =============================================================================

@app.callback(
    [Output("loading-output", "children"),
     Output("last-update-time", "children"),
     Output("flight-dropdown", "options"),
     Output("flight-dropdown", "value"),
     Output("kpi-total-flights", "children"),
     Output("kpi-anomalies", "children"),
     Output("kpi-restricted", "children"), # Nouveau Output
     Output("kpi-ratio", "children"),
     Output("kpi-last-contact", "children"),
     Output("critical-table", "data"),
     Output("pie-chart", "figure"),
     Output("box-plot", "figure")],
    [Input("btn-update", "n_clicks")],
    prevent_initial_call=False
)
def update_data(n_clicks):
    global global_df
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if triggered_id == "btn-update" and n_clicks > 0:
        try:
            load_data_from_websocket(nb_messages=5000, output_file=RAW_FILE) # Réduit à 5000 pour rapidité démo
            process_flight_data(input_csv_path=RAW_FILE, output_csv_path=TRANSFORMED_FILE)
            global_df = load_and_predict_data()
        except Exception as e:
            print(f"Erreur update : {e}")
    
    if global_df.empty:
        return "", "Jamais", [], None, "0", "0", "0", "0%", "-", [], {}, {}

    unique_flights = global_df.groupby('flight_id').first().reset_index()
    
    # Options Dropdown
    dropdown_options = [
        {'label': f"{row['callsign']} ({row['flight_id']}) - {row['predicted_anomaly']}", 'value': row['flight_id']}
        for idx, row in unique_flights.iterrows()
    ]
    default_value = dropdown_options[0]['value'] if dropdown_options else None
    
    # Calcul KPIs
    total_flights = len(unique_flights)
    
    # Vols avec anomalies IA
    nb_anomalies = 0
    if 'predicted_anomaly' in unique_flights.columns:
        nb_anomalies = len(unique_flights[unique_flights['predicted_anomaly'] != 'Normal'])
        
    # Vols en zone restreinte (On regarde dans global_df pour ne pas rater un point intermédiaire)
    # On compte les flight_id uniques qui ont au moins un point à 1
    if 'in_restricted_zone' in global_df.columns:
        flights_in_zone = global_df[global_df['in_restricted_zone'] == 1]['flight_id'].unique()
        nb_restricted = len(flights_in_zone)
    else:
        nb_restricted = 0

    ratio = f"{(nb_anomalies/total_flights*100):.1f}%" if total_flights > 0 else "0%"
    last_contact = global_df['timestamp'].max().strftime('%H:%M:%S') + " UTC+0"

    # Tableau Critique (IA Anormale OU Zone Restreinte)
    critical_data = []
    # On récupère les vols critiques
    crit_ids = []
    if 'predicted_anomaly' in unique_flights.columns:
        crit_ids = unique_flights[unique_flights['predicted_anomaly'] != 'Normal']['flight_id'].tolist()
    
    # On ajoute ceux qui sont dans une zone restreinte
    if 'in_restricted_zone' in global_df.columns:
        zone_ids = global_df[global_df['in_restricted_zone'] == 1]['flight_id'].unique().tolist()
        crit_ids = list(set(crit_ids + zone_ids)) # Union des deux listes

    if crit_ids:
        # On filtre le dataset global pour récupérer les dernières infos de ces vols
        # On prend le dernier point de chaque vol critique
        last_points = global_df[global_df['flight_id'].isin(crit_ids)].sort_values('timestamp', ascending=False).groupby('flight_id').first().reset_index()
        # On trie par heure récente et on prend les 5 premiers
        top_critical = last_points.sort_values('timestamp', ascending=False).head(5)
        
        for idx, row in top_critical.iterrows():
            critical_data.append({
                "flight_id": row['flight_id'],
                "callsign": row['callsign'],
                "predicted_anomaly": row.get('predicted_anomaly', 'N/A'),
                "in_restricted_zone": row.get('in_restricted_zone', 0),
                "ground_speed": row['ground_speed'],
                "altitude": row['altitude'],
                "timestamp": row['timestamp'].strftime('%H:%M:%S')
            })

    # Graphs Stats
    status_counts = unique_flights['predicted_anomaly'].value_counts().reset_index() if 'predicted_anomaly' in unique_flights.columns else pd.DataFrame(columns=['index', 'predicted_anomaly'])
    status_counts.columns = ['Status', 'Count']
    fig_pie = px.pie(status_counts, values='Count', names='Status', title="Répartition IA", color_discrete_sequence=px.colors.qualitative.Pastel)
    fig_pie.update_layout(paper_bgcolor=colors['card'], font_color='white')

    fig_box = px.box(global_df, x='predicted_anomaly', y='altitude', title="Altitude vs IA", color='predicted_anomaly')
    fig_box.update_layout(paper_bgcolor=colors['card'], font_color='white', plot_bgcolor=colors['card'])

    return "", time.strftime('%H:%M:%S'), dropdown_options, default_value, str(total_flights), str(nb_anomalies), str(nb_restricted), ratio, last_contact, critical_data, fig_pie, fig_box

@app.callback(
    [Output("flight-details-panel", "children"),
     Output("map-graph", "figure"),
     Output("deviation-graph", "figure"),
     Output("altitude-graph", "figure"),
     Output("speed-graph", "figure")],
    [Input("flight-dropdown", "value")]
)
def update_flight_details(selected_flight_id):
    if not selected_flight_id or global_df.empty:
        return "Sélectionnez un vol", {}, {}, {}, {}

    dff = global_df[global_df['flight_id'] == selected_flight_id].sort_values('timestamp')
    if dff.empty: return "Pas de données", {}, {}, {}, {}

    # Info Panel
    main_status = dff['predicted_anomaly'].mode()[0] if 'predicted_anomaly' in dff.columns else "Inconnu"
    in_zone = 1 in dff['in_restricted_zone'].values if 'in_restricted_zone' in dff.columns else False
    
    status_color = colors['success'] if main_status == 'Normal' else colors['danger']
    zone_msg = "⚠️ A TRAVERSÉ UNE ZONE RESTREINTE" if in_zone else "✅ Trajet Autorisé"
    zone_color = colors['warning'] if in_zone else colors['success']

    info_panel = html.Div([
        html.Div([
            html.Span("Statut IA : ", style={'fontWeight': 'bold'}),
            html.Span(main_status.upper(), style={'color': status_color, 'fontWeight': 'bold', 'marginLeft': '10px', 'marginRight': '20px'}),
            html.Span("Zones : ", style={'fontWeight': 'bold'}),
            html.Span(zone_msg, style={'color': zone_color, 'fontWeight': 'bold', 'marginLeft': '10px'})
        ]),
        html.Div([
            f"Début: {dff['timestamp'].iloc[0].strftime('%H:%M:%S')} | Fin: {dff['timestamp'].iloc[-1].strftime('%H:%M:%S')}"
        ], style={'marginTop': '10px', 'color': '#aaa'})
    ])

    # CARTE AVEC ZONES RESTREINTES
    # 1. Tracé de l'avion
    fig_map = px.scatter_mapbox(
        dff, lat="latitude", lon="longitude", color="altitude",
        hover_data=["ground_speed", "heading", "in_restricted_zone"],
        zoom=5, height=450
    )
    
    # 2. Ajout des zones restreintes (Rectangles Rouges)
    # On utilise go.Scattermapbox avec mode 'lines' et fill 'toself' pour faire des polygones
    for zone in RESTRICTED_ZONES:
        # zone = [(lat, lon), (lat, lon), ...]
        # Pour fermer le polygone, il faut répéter le premier point à la fin si ce n'est pas fait
        lats = [p[0] for p in zone] + [zone[0][0]]
        lons = [p[1] for p in zone] + [zone[0][1]]
        
        fig_map.add_trace(go.Scattermapbox(
            mode="lines",
            lon=lons, lat=lats,
            fill='toself',
            fillcolor='rgba(231, 76, 60, 0.3)', # Rouge semi-transparent
            line=dict(width=1, color='#e74c3c'),
            name="Zone Restreinte",
            hoverinfo='text',
            text='ZONE INTERDITE'
        ))

    fig_map.update_layout(mapbox_style="carto-darkmatter", margin={"r":0,"t":0,"l":0,"b":0}, paper_bgcolor=colors['card'])
    # Légende inutilement verbeuse sur la carte, on peut la cacher
    fig_map.update_layout(showlegend=False)

    # Autres graphiques
    fig_dev = px.area(dff, x='timestamp', y='deviation_m', title="Déviation (m)")
    fig_dev.update_layout(paper_bgcolor=colors['card'], font_color='white', plot_bgcolor=colors['card'])
    fig_dev.update_traces(line_color=colors['danger'])

    fig_alt = px.line(dff, x='timestamp', y='altitude', title="Altitude (ft)")
    fig_alt.update_layout(paper_bgcolor=colors['card'], font_color='white', plot_bgcolor=colors['card'])
    
    fig_speed = px.line(dff, x='timestamp', y='ground_speed', title="Vitesse (kts)")
    fig_speed.update_layout(paper_bgcolor=colors['card'], font_color='white', plot_bgcolor=colors['card'])
    fig_speed.update_traces(line_color=colors['warning'])

    return info_panel, fig_map, fig_dev, fig_alt, fig_speed

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=8050, debug=True)
