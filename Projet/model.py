import joblib
import pandas as pd
import os

class FlightModel:
    def __init__(self, model_folder="models"):
        self.model_path = os.path.join(model_folder, "random_forest.joblib")
        self.encoder_path = os.path.join(model_folder, "label_encoder.joblib")
        self.model = None
        self.encoder = None
        self.features = ["latitude", "longitude", "altitude", "ground_speed", 
                         "heading", "autopilot_on", "deviation_m"]

    def load_model(self):
        """Charge le modèle et l'encodeur en mémoire."""
        if not os.path.exists(self.model_path) or not os.path.exists(self.encoder_path):
            raise FileNotFoundError("Les fichiers du modèle sont introuvables. Lancez train_model.py d'abord.")
        
        print("Chargement du modèle Random Forest...")
        self.model = joblib.load(self.model_path)
        self.encoder = joblib.load(self.encoder_path)
        print("Modèle chargé avec succès.")

    def predict(self, data):
        """
        Effectue une prédiction sur de nouvelles données.
        :param data: Dictionnaire ou DataFrame contenant les features requises.
        :return: Le nom de l'anomalie (ex: 'Normal', 'Hijack'...)
        """
        if self.model is None:
            self.load_model()

        # Transformation en DataFrame si c'est un dictionnaire
        if isinstance(data, dict):
            df = pd.DataFrame([data])
        elif isinstance(data, pd.DataFrame):
            df = data.copy()
        else:
            raise ValueError("Format de données non supporté. Utilisez un dict ou un DataFrame.")

        # Vérification et ordre des colonnes (CRUCIAL pour Random Forest)
        try:
            df = df[self.features]
        except KeyError as e:
            raise KeyError(f"Il manque des colonnes dans les données d'entrée : {e}")

        # Prédiction (retourne des chiffres 0, 1, 2...)
        prediction_idx = self.model.predict(df)
        
        # Décodage (retourne les strings "Normal", "Emergency"...)
        prediction_labels = self.encoder.inverse_transform(prediction_idx)

        return prediction_labels

# --- Exemple d'utilisation autonome ---
if __name__ == "__main__":
    # Création de données factices pour tester
    df_prepared = pd.read_csv("test_data_transformed.csv")

    try:
        flight_ai = FlightModel()
        flight_ai.load_model()
        result = flight_ai.predict(df_prepared.iloc[:5])  # Prédit les 5 premières lignes
        print(f"Prédiction pour les données de test : {result[0]}")
    except Exception as e:
        print(f"Erreur lors du test : {e}")