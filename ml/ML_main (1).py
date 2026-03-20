from fastapi import FastAPI, HTTPException
from ml_utils import predire_6h, VILLES

app = FastAPI()

@app.get("/api/predict/temperature/{city}")
async def predict_temperature(city: str):
    """
    Prédit la température pour les 6 prochaines heures.
    Exemple : GET /api/predict/temperature/Lyon
    """
    # Vérifier que la ville est supportée
    if city not in VILLES:
        raise HTTPException(
            status_code=404,
            detail=f"Ville '{city}' non supportée. Villes disponibles : {list(VILLES.keys())}"
        )

    # Faire la prédiction
    resultat = predire_6h(city)
    return resultat
