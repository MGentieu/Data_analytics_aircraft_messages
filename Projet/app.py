import dash
from dash import dcc, html, Input, Output, State, dash_table
import plotly.express as px
import pandas as pd
import os
import time

# Import de vos modules personnalisés
from recuperation_donnees import load_data_from_websocket
from transform_data import process_flight_data
from model import FlightModel

# =============================================================================
# 1. INITIALISATION ET CHARGEMENT DU MODÈLE
# =============================================================================

# Chargement du modèle une seule fois au démarrage
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
RAW_FILE = "test_data_dashboard.csv"
TRANSFORMED_FILE = "test_data_transformed.csv"

# =============================================================================
# 2. LOGIQUE MÉTIER ET DONNÉES
# =============================================================================

def load_and_predict_data():
    """
    Charge les données transformées et applique le modèle IA sur l'ensemble.
    Retourne un DataFrame enrichi avec une colonne 'predicted_anomaly'.
    """
    if not os.path.exists(TRANSFORMED_FILE):
        return pd.DataFrame()

    df = pd.read_csv(TRANSFORMED_FILE)
    
    # Conversion temporelle
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Si le modèle est chargé, on fait les prédictions
    if MODEL_LOADED and not df.empty:
        try:
            # On prédit ligne par ligne (ou par bloc)
            # Note: Le modèle attend des colonnes spécifiques, gérées par ai_pilot.predict
            # predict retourne une liste de strings, on l'assigne directement
            print("Lancement des prédictions sur le dataset...")
            df['predicted_anomaly'] = ai_pilot.predict(df)
        except Exception as e:
            print(f"Erreur prédiction : {e}")
            df['predicted_anomaly'] = "Non calculé"
    else:
        df['predicted_anomaly'] = "Modèle non chargé"
    
    return df

# Chargement initial des données en mémoire
global_df = load_and_predict_data()

# =============================================================================
# 3. CONFIGURATION DASH
# =============================================================================

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server

colors = {
    'background': '#1a1c23',    # Fond sombre style radar
    'card': '#2c313c',          # Gris anthracite pour les cartes
    'text': '#ffffff',          # Texte blanc
    'accent': '#3498db',        # Bleu
    'danger': '#e74c3c',        # Rouge alerte
    'success': '#2ecc71'        # Vert normal
}

# =============================================================================
# 4. LAYOUT
# =============================================================================

def create_card(title, value, id_value, color=colors['text']):
    return html.Div([
        html.H6(title, style={'color': '#aaaaaa', 'marginBottom': '5px'}),
        html.H2(value, id=id_value, style={'color': color, 'fontWeight': 'bold', 'marginTop': '0px'})
    ], style={'backgroundColor': colors['card'], 'padding': '20px', 'borderRadius': '8px', 'textAlign': 'center'})

app.layout = html.Div(style={'backgroundColor': colors['background'], 'color': colors['text'], 'minHeight': '100vh', 'padding': '20px', 'fontFamily': 'Segoe UI, sans-serif'}, children=[
    
    # --- HEADER ---
    html.Div([
        html.H1("✈️ ADS-B SENTINEL", style={'float': 'left', 'fontWeight': 'bold', 'letterSpacing': '2px'}),
        html.Div([
            html.Button("🔄 Mettre à jour les données", id='btn-update', n_clicks=0, 
                       style={'backgroundColor': colors['accent'], 'color': 'white', 'border': 'none', 'fontSize': '16px', 'padding': '10px 20px', 'cursor': 'pointer'}),
            html.Div(id='last-update-time', style={'marginTop': '5px', 'fontSize': '12px', 'color': '#888'})
        ], style={'float': 'right'}),
        html.Div(style={'clear': 'both'})
    ], style={'marginBottom': '30px', 'borderBottom': '1px solid #444', 'paddingBottom': '20px'}),

    # --- BARRE DE CHARGEMENT / NOTIFICATIONS ---
    dcc.Loading(
        id="loading-data",
        type="default",
        children=html.Div(id="loading-output", style={'display': 'none'})
    ),

    # --- KPIs GLOBAUX ---
    html.Div([
        html.Div(create_card("Vols Suivis", "0", "kpi-total-flights"), className="three columns"),
        html.Div(create_card("Alertes Actives", "0", "kpi-anomalies", colors['danger']), className="three columns"),
        html.Div(create_card("Taux Anomalie", "0%", "kpi-ratio"), className="three columns"),
        html.Div(create_card("Dernier Contact", "-", "kpi-last-contact"), className="three columns"),
    ], className="row", style={'marginBottom': '30px'}),

    # --- SECTION CRITIQUE ---
    html.H4("⚠️ Top 5 : Vols Critiques (Détection IA)", style={'color': colors['danger'], 'borderLeft': f"5px solid {colors['danger']}", 'paddingLeft': '10px'}),
    html.Div([
        dash_table.DataTable(
            id='critical-table',
            columns=[
                {"name": "Flight ID", "id": "flight_id"},
                {"name": "Callsign", "id": "callsign"},
                {"name": "Dernière Anomalie", "id": "predicted_anomaly"},
                {"name": "Dernière Vitesse", "id": "ground_speed"},
                {"name": "Altitude", "id": "altitude"},
                {"name": "Heure", "id": "timestamp"}
            ],
            style_header={'backgroundColor': '#2c313c', 'color': 'white', 'fontWeight': 'bold', 'border': '1px solid #444'},
            style_cell={'backgroundColor': '#1a1c23', 'color': 'white', 'border': '1px solid #444', 'textAlign': 'left'},
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#23262e'}
            ]
        )
    ], style={'marginBottom': '40px'}),

    # --- ANALYSE DÉTAILLÉE ---
    html.Div([
        html.H4("🔎 Analyse Détaillée par Vol", style={'color': colors['accent'], 'borderLeft': f"5px solid {colors['accent']}", 'paddingLeft': '10px'}),
        
        # Sélecteur
        html.Div([
            html.Label("Sélectionner un vol :"),
            dcc.Dropdown(
                id='flight-dropdown',
                style={'color': '#000'} # Dropdown needs black text for readability
            )
        ], style={'marginBottom': '20px'}),

        # Info Vol
        html.Div([
            html.Div(id='flight-details-panel', style={'padding': '15px', 'backgroundColor': colors['card'], 'borderRadius': '5px', 'marginBottom': '20px'})
        ]),

        # Graphiques Ligne 1
        html.Div([
            html.Div([dcc.Graph(id='map-graph')], className="eight columns"),
            html.Div([dcc.Graph(id='deviation-graph')], className="four columns"),
        ], className="row"),

        # Graphiques Ligne 2
        html.Div([
            html.Div([dcc.Graph(id='altitude-graph')], className="six columns"),
            html.Div([dcc.Graph(id='speed-graph')], className="six columns"),
        ], className="row", style={'marginTop': '20px'}),

        # Stats globales
        html.H4("📊 Statistiques Globales Dataset", style={'marginTop': '40px', 'borderTop': '1px solid #444', 'paddingTop': '20px'}),
        html.Div([
            html.Div([dcc.Graph(id='pie-chart')], className="six columns"),
            html.Div([dcc.Graph(id='box-plot')], className="six columns"),
        ], className="row")

    ])
])

# =============================================================================
# 5. CALLBACKS
# =============================================================================

# --- Callback 1 : Mise à jour des données (Bouton) ---
@app.callback(
    [Output("loading-output", "children"),
     Output("last-update-time", "children"),
     Output("flight-dropdown", "options"),
     Output("flight-dropdown", "value"),
     Output("kpi-total-flights", "children"),
     Output("kpi-anomalies", "children"),
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

    # Si déclenché par le bouton, on lance les scripts
    if triggered_id == "btn-update" and n_clicks > 0:
        print(">>> Bouton cliqué : Lancement récupération...")
        # 1. Récupération (On limite à 1000 messages pour que l'UI ne freeze pas trop longtemps)
        try:
            load_data_from_websocket(nb_messages=1000, output_file=RAW_FILE)
            print(">>> Récupération terminée.")
        except Exception as e:
            print(f"Erreur Récupération : {e}")

        # 2. Transformation
        try:
            print(">>> Lancement transformation...")
            process_flight_data(input_csv_path=RAW_FILE, output_csv_path=TRANSFORMED_FILE)
            print(">>> Transformation terminée.")
        except Exception as e:
            print(f"Erreur Transformation : {e}")
        
        # 3. Rechargement dataframe
        global_df = load_and_predict_data()
    
    # --- Préparation des Données pour l'UI ---
    if global_df.empty:
        return "", "Jamais", [], None, "0", "0", "0%", "-", [], {}, {}

    # Dropdown options
    # On groupe par flight_id pour avoir une liste unique
    unique_flights = global_df.groupby('flight_id').first().reset_index()
    # On ajoute le status prédit dans le label pour aider le choix
    dropdown_options = [
        {'label': f"{row['callsign']} ({row['flight_id']}) - {row['predicted_anomaly']}", 'value': row['flight_id']}
        for idx, row in unique_flights.iterrows()
    ]
    # Sélection par défaut (le premier critique, sinon le premier tout court)
    default_value = dropdown_options[0]['value'] if dropdown_options else None
    
    # KPIs
    total_flights = len(unique_flights)
    # Compte des anomalies prédites (excluant "Normal")
    if 'predicted_anomaly' in unique_flights.columns:
        critical_flights = unique_flights[unique_flights['predicted_anomaly'] != 'Normal']
        nb_anomalies = len(critical_flights)
    else:
        nb_anomalies = 0
        
    ratio = f"{(nb_anomalies/total_flights*100):.1f}%" if total_flights > 0 else "0%"
    last_contact = global_df['timestamp'].max().strftime('%H:%M:%S')

    # Tableau Critique (Top 5 récents avec anomalie)
    critical_data = []
    if nb_anomalies > 0:
        # On prend les 5 plus récents
        top_critical = critical_flights.sort_values('timestamp', ascending=False).head(5)
        for idx, row in top_critical.iterrows():
            critical_data.append({
                "flight_id": row['flight_id'],
                "callsign": row['callsign'],
                "predicted_anomaly": row['predicted_anomaly'],
                "ground_speed": row['ground_speed'],
                "altitude": row['altitude'],
                "timestamp": row['timestamp'].strftime('%H:%M:%S')
            })

    # Graphiques Globaux
    # Pie Chart
    status_counts = unique_flights['predicted_anomaly'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Count']
    fig_pie = px.pie(status_counts, values='Count', names='Status', title="Répartition IA des Vols", 
                     color_discrete_sequence=px.colors.qualitative.Pastel)
    fig_pie.update_layout(paper_bgcolor=colors['card'], font_color='white')

    # Box Plot (Altitude par Anomaly)
    fig_box = px.box(global_df, x='predicted_anomaly', y='altitude', title="Altitude vs Anomalie",
                     color='predicted_anomaly')
    fig_box.update_layout(paper_bgcolor=colors['card'], font_color='white', plot_bgcolor=colors['card'])

    update_msg = f"Dernière mise à jour : {time.strftime('%H:%M:%S')}"
    
    return "", update_msg, dropdown_options, default_value, str(total_flights), str(nb_anomalies), ratio, last_contact, critical_data, fig_pie, fig_box


# --- Callback 2 : Détails du vol sélectionné ---
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
    
    if dff.empty:
        return "Pas de données pour ce vol", {}, {}, {}, {}

    # Données Vol
    first_seen = dff['timestamp'].iloc[0].strftime('%d/%m %H:%M:%S')
    last_seen = dff['timestamp'].iloc[-1].strftime('%H:%M:%S')
    duration = str(dff['timestamp'].iloc[-1] - dff['timestamp'].iloc[0])
    
    # Statut IA (On prend le plus fréquent ou le pire)
    statuses = dff['predicted_anomaly'].value_counts()
    main_status = statuses.idxmax()
    
    # Construction panneau info
    status_color = colors['success'] if main_status == 'Normal' else colors['danger']
    
    info_panel = html.Div([
        html.Div([
            html.Span("Statut IA : ", style={'fontWeight': 'bold'}),
            html.Span(main_status.upper(), style={'color': status_color, 'fontWeight': 'bold', 'fontSize': '18px', 'marginLeft': '10px'})
        ], style={'marginBottom': '10px'}),
        
        html.Div([
            html.Div(f"📅 Début : {first_seen}", className="four columns"),
            html.Div(f"🏁 Fin : {last_seen}", className="four columns"),
            html.Div(f"⏱️ Durée : {duration}", className="four columns"),
        ], className="row")
    ])

    # Graphiques
    # Carte
    fig_map = px.scatter_mapbox(
        dff, lat="latitude", lon="longitude", color="altitude",
        hover_data=["ground_speed", "heading", "predicted_anomaly"],
        zoom=5, height=400
    )
    fig_map.update_layout(mapbox_style="carto-darkmatter", margin={"r":0,"t":0,"l":0,"b":0}, paper_bgcolor=colors['card'])

    # Deviation
    fig_dev = px.area(dff, x='timestamp', y='deviation_m', title="Déviation de trajectoire (m)")
    fig_dev.update_layout(paper_bgcolor=colors['card'], font_color='white', plot_bgcolor=colors['card'])
    fig_dev.update_traces(line_color=colors['danger'])

    # Altitude
    fig_alt = px.line(dff, x='timestamp', y='altitude', title="Profil Altitude")
    fig_alt.update_layout(paper_bgcolor=colors['card'], font_color='white', plot_bgcolor=colors['card'])
    fig_alt.update_traces(line_color=colors['accent'])

    # Speed
    fig_speed = px.line(dff, x='timestamp', y='ground_speed', title="Vitesse Sol (kts)")
    fig_speed.update_layout(paper_bgcolor=colors['card'], font_color='white', plot_bgcolor=colors['card'])
    fig_speed.update_traces(line_color='#f1c40f') # Jaune

    return info_panel, fig_map, fig_dev, fig_alt, fig_speed


if __name__ == '__main__':
    print("Démarrage du Serveur Dash...")
    app.run(debug=True)