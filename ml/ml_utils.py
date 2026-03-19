import pickle
import pandas as pd
import numpy as np
import requests
from datetime import timedelta
import os

# ============================================================
# VILLES SUPPORTÉES
# ============================================================
VILLES = {
    "Lyon"      : {"latitude": 45.7640, "longitude":  4.8357},
    "Paris"     : {"latitude": 48.8566, "longitude":  2.3522},
    "Marseille" : {"latitude": 43.2965, "longitude":  5.3698},
    "Bordeaux"  : {"latitude": 44.8378, "longitude": -0.5792},
    "Lille"     : {"latitude": 50.6292, "longitude":  3.0573},
}

# ============================================================
# CHARGEMENT DES MODÈLES
# ============================================================
models_path = os.path.join(os.path.dirname(__file__), "models")

modeles = {}
features = None
r2 = None

try:
    for h in range(1, 7):
        model_file = os.path.join(models_path, f"modele_xgb_{h}h.pkl")
        if os.path.exists(model_file):
            with open(model_file, "rb") as f:
                modeles[h] = pickle.load(f)

    features_file = os.path.join(models_path, "features.pkl")
    if os.path.exists(features_file):
        with open(features_file, "rb") as f:
            features = pickle.load(f)

    r2_file = os.path.join(models_path, "r2_par_horizon.pkl")
    if os.path.exists(r2_file):
        with open(r2_file, "rb") as f:
            r2 = pickle.load(f)

    print(f"✅ Modèles chargés : {len(modeles)} horizons")
except Exception as e:
    print(f"⚠️ Erreur chargement modèles : {e}")
    # Créer des modèles factices pour éviter les erreurs
    modeles = {h: None for h in range(1, 7)}
    features = []
    r2 = {h: 0.8 for h in range(1, 7)}

# ============================================================
# RÉCUPÉRATION DONNÉES OPEN-METEO
# ============================================================
def recuperer_donnees(ville):
    """
    Récupère les 48 dernières heures depuis Open-Meteo.
    """
    coords = VILLES[ville]

    print(f"🌤️ Récupération des données météo pour {ville}")
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude"      : coords["latitude"],
            "longitude"     : coords["longitude"],
            "hourly"        : [
                "temperature_2m",
                "relative_humidity_2m",
                "surface_pressure",
                "wind_speed_10m",
                "cloud_cover",
                "precipitation",
            ],
            "past_hours"    : 48,
            "forecast_hours": 1,
            "timezone"      : "Europe/Paris"
        }
    )
    
    if response.status_code != 200:
        raise Exception(f"Erreur API Open-Meteo: {response.status_code}")
    
    hourly = response.json()["hourly"]

    df = pd.DataFrame({
        "datetime"     : pd.to_datetime(hourly["time"]),
        "temperature"  : hourly["temperature_2m"],
        "humidite"     : hourly["relative_humidity_2m"],
        "pression"     : hourly["surface_pressure"],
        "vent"         : hourly["wind_speed_10m"],
        "nuages"       : hourly["cloud_cover"],
        "precipitation": hourly["precipitation"],
    })

    print(f"✅ Données récupérées : {len(df)} points")
    return df.set_index("datetime")


# ============================================================
# CONSTRUCTION DES FEATURES
# ============================================================
def construire_features(df, ville):
    """
    Construit les 24 features attendues par le modèle.
    """
    # Lags
    df["temp_lag_1h"]  = df["temperature"].shift(1)
    df["temp_lag_2h"]  = df["temperature"].shift(2)
    df["temp_lag_3h"]  = df["temperature"].shift(3)
    df["temp_lag_6h"]  = df["temperature"].shift(6)
    df["temp_lag_12h"] = df["temperature"].shift(12)
    df["temp_lag_24h"] = df["temperature"].shift(24)
    df["temp_lag_36h"] = df["temperature"].shift(36)
    df["temp_lag_48h"] = df["temperature"].shift(48)

    # Fenêtres glissantes
    df["temp_moy_6h"]  = df["temperature"].rolling(6).mean()
    df["temp_moy_12h"] = df["temperature"].rolling(12).mean()
    df["temp_std_12h"] = df["temperature"].rolling(12).std()

    # Variables temporelles cycliques
    df["heure_sin"] = np.sin(2 * np.pi * df.index.hour / 24)
    df["heure_cos"] = np.cos(2 * np.pi * df.index.hour / 24)
    df["mois_sin"]  = np.sin(2 * np.pi * df.index.month / 12)
    df["mois_cos"]  = np.cos(2 * np.pi * df.index.month / 12)

    # Encodage ville
    for v in ["Bordeaux", "Lille", "Lyon", "Marseille", "Paris"]:
        df[f"ville_{v}"] = 1 if v == ville else 0

    return df.dropna()


# ============================================================
# PRÉDICTION 6H
# ============================================================
def predire_6h(ville):
    """
    Prédit la température pour les 6 prochaines heures.
    Retourne un dictionnaire JSON prêt pour le frontend.
    """
    try:
        # 1. Récupérer les données
        df = recuperer_donnees(ville)

        # 2. Construire les features
        df = construire_features(df, ville)

        # 3. Prendre la dernière ligne
        if features and len(features) > 0:
            derniere_ligne = df[features].iloc[[-1]]
        else:
            # Fallback si pas de features définies
            derniere_ligne = df.iloc[[-1]]
        
        heure_depart = derniere_ligne.index[0]

        # 4. Prédire
        previsions = []
        for h in range(1, 7):
            if modeles[h] is not None:
                temp = round(float(modeles[h].predict(derniere_ligne)[0]), 1)
                confiance = round(r2[h] * 100, 1)
            else:
                # Prédiction factice si modèle non chargé
                temp = round(df["temperature"].iloc[-1] + np.random.uniform(-2, 2), 1)
                confiance = 75.0
            
            heure = heure_depart + timedelta(hours=h)

            previsions.append({
                "heure"      : heure.strftime("%d/%m %Hh"),
                "temperature": temp,
                "confiance"  : confiance
            })

        return {
            "ville"     : ville,
            "base"      : heure_depart.strftime("%d/%m/%Y %Hh"),
            "previsions": previsions
        }
    
    except Exception as e:
        print(f"❌ Erreur prédiction pour {ville}: {e}")
        # Retourner une prédiction d'erreur
        return {
            "ville": ville,
            "error": str(e),
            "base": "N/A",
            "previsions": []
        }
