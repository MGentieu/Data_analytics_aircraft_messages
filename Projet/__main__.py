import os
import dash
from dash import dcc, html, Input, Output, State, dash_table
import plotly.express as px
import pandas as pd
import os
import time
import subprocess
import sys

from recuperation_donnees import load_data_from_websocket
from transform_data import process_flight_data
from model import FlightModel

if __name__ == "__main__":
    # Étape 1 : Récupération des données brutes
    if not os.path.exists("raw_data.csv"):
        load_data_from_websocket(output_file="raw_data.csv", nb_messages=10000)
        process_flight_data(input_csv_path="raw_data.csv", output_csv_path="flight_data_transformed.csv")

    os.system("python app.py")
