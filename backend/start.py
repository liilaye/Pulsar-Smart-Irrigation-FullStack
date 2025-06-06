
#!/usr/bin/env python3
"""
Script de démarrage pour le backend Flask PulsarInfinite
"""

import os
import sys
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Ajouter le dossier backend au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

if __name__ == '__main__':
    app = create_app()
    
    print("=" * 60)
    print("🚀 Backend Flask PulsarInfinite")
    print("=" * 60)
    print("📡 MQTT Broker: http://217.182.210.54:8080")
    print("🌤️ Service météo: OpenWeather API")
    print("🤖 Modèle ML: XGBoost arrosage")
    print("💾 Base de données: SQLite (irrigation_logs.db)")
    print("🌐 API disponible sur: http://localhost:5002/api")
    print("=" * 60)
    
    # Vérifications au démarrage
    if not os.getenv("OPENWEATHER_API_KEY"):
        print("⚠️  OPENWEATHER_API_KEY non définie - météo en mode fallback")
    
    model_path = os.path.join(os.path.dirname(__file__), 'models', 'xgboost_arrosage_litres.pkl')
    if not os.path.exists(model_path):
        print(f"⚠️  Modèle ML non trouvé: {model_path}")
        print("📍 Placez xgboost_arrosage_litres.pkl dans backend/models/")
    
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5002, use_reloader=False)
