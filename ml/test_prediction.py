import json
from ml_utils import predire_6h

# --- Test pour Lyon ---
resultat = predire_6h("Lyon")
print(json.dumps(resultat, indent=2, ensure_ascii=False))

# --- Test pour Paris ---
resultat = predire_6h("Paris")
print(json.dumps(resultat, indent=2, ensure_ascii=False))