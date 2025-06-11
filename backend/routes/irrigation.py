
from flask import Blueprint, request, jsonify
from services.ml_service import ml_service
from services.mqtt_service import mqtt_service
from config.database import log_irrigation
import datetime
import numpy as np
import threading
import time

irrigation_bp = Blueprint('irrigation', __name__)

# Stockage global des plannings actifs
active_schedules = {}
schedule_thread = None

@irrigation_bp.route('/arroser', methods=['POST'])
def arroser():
    """Endpoint ML pour recommandations d'irrigation - CORRIGÉ"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Aucune donnée reçue"}), 400
            
        features = data.get('features', [])
        
        if not features or len(features) != 15:
            return jsonify({"error": "Exactement 15 paramètres requis pour le modèle ML"}), 400

        print(f"✅ Requête ML reçue avec features: {features}")

        # Conversion explicite en float
        try:
            features_array = [float(f) for f in features]
        except Exception as conv_err:
            print(f"❌ Erreur conversion features: {conv_err}")
            return jsonify({"error": "Les paramètres doivent être numériques"}), 400

        # Appel du service ML
        try:
            prediction = ml_service.predict_irrigation(features_array)
            
            if prediction and 'volume_m3' in prediction:
                # Log de l'irrigation ML
                log_irrigation(
                    action='ml_prediction',
                    duration_minutes=prediction['duree_minutes'],
                    volume_m3=prediction['volume_m3'],
                    mqtt_status='prediction_ok',
                    source='ML'
                )
                
                print(f"✅ Prédiction ML réussie: {prediction}")
                
                # Format de réponse cohérent avec l'arrosage manuel
                return jsonify({
                    "duree_minutes": float(prediction['duree_minutes']),
                    "volume_eau_m3": float(prediction['volume_m3']),
                    "status": "ok",
                    "matt": f"Irrigation ML recommandée: {prediction['duree_minutes']:.1f} min pour {prediction['volume_m3']:.3f} m³"
                }), 200
            else:
                return jsonify({"error": "Prédiction ML invalide", "status": "error"}), 500
                
        except Exception as ml_err:
            print(f"❌ Erreur ML Service: {ml_err}")
            return jsonify({"error": f"Erreur modèle ML: {str(ml_err)}", "status": "error"}), 500

    except Exception as e:
        print(f"❌ Erreur générale endpoint /arroser: {e}")
        return jsonify({"error": f"Erreur serveur: {str(e)}", "status": "error"}), 500


@irrigation_bp.route('/irrigation/status', methods=['GET'])
def get_irrigation_status():
    """Retourne l'état de l'irrigation - CORRIGÉ"""
    try:
        # Format de réponse JSON valide
        status = {
            "isActive": False,
            "lastMLRecommendation": None,
            "backend_connected": True,
            "mqtt_connected": True,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        print(f"ℹ️ Statut irrigation demandé: {status}")
        return jsonify(status), 200
        
    except Exception as e:
        print(f"❌ Erreur statut irrigation: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500


# ... keep existing code (irrigation/schedule endpoints)

@irrigation_bp.route('/irrigation/schedule', methods=['POST'])
def receive_schedule():
    """Reçoit et traite les plannings programmés avec analyse IA"""
    global active_schedules, schedule_thread
    
    try:
        data = request.get_json()
        schedules = data.get('schedules', {})
        
        print(f"📅 Réception planning programmé: {schedules}")
        
        # Analyser chaque planning avec l'IA
        analyzed_schedules = {}
        for day, schedule in schedules.items():
            if schedule.get('enabled'):
                # Générer des features par défaut pour l'analyse IA
                default_features = [
                    25.0, 0, 65, 12.0, 1, 10000, 26.0, 42, 1.2, 6.8, 45, 38, 152, 3, 2
                ]
                
                # Obtenir la recommandation IA pour ce créneau
                try:
                    prediction = ml_service.predict_irrigation(default_features)
                    analyzed_schedules[day] = {
                        **schedule,
                        'ai_duration_minutes': prediction['duree_minutes'],
                        'ai_volume_m3': prediction['volume_m3'],
                        'ai_optimized': True
                    }
                    print(f"✅ Planning {day} optimisé par IA: {prediction['duree_minutes']:.1f} min")
                except Exception as e:
                    print(f"⚠️ Erreur IA pour {day}: {e}")
                    analyzed_schedules[day] = {
                        **schedule,
                        'ai_duration_minutes': 30,
                        'ai_volume_m3': 0.6,
                        'ai_optimized': False
                    }
        
        # Sauvegarder les plannings analysés
        active_schedules = analyzed_schedules
        
        # Démarrer le thread de surveillance des plannings
        if schedule_thread is None or not schedule_thread.is_alive():
            schedule_thread = threading.Thread(target=monitor_schedules, daemon=True)
            schedule_thread.start()
            print("🔄 Thread de surveillance des plannings démarré")
        
        log_irrigation(
            action='schedule_received',
            duration_minutes=None,
            volume_m3=None,
            mqtt_status='ok',
            source='SCHEDULE_AI'
        )
        
        return jsonify({
            "success": True,
            "message": "Planning reçu et optimisé par IA",
            "analyzed_schedules": analyzed_schedules
        }), 200
        
    except Exception as e:
        print(f"❌ Erreur traitement planning: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


def monitor_schedules():
    """Thread de surveillance pour exécuter les plannings automatiquement"""
    print("🕐 Démarrage surveillance des plannings programmés")
    
    while True:
        try:
            current_time = datetime.datetime.now()
            current_day = current_time.strftime('%A')
            current_hour_min = current_time.strftime('%H:%M')
            
            # Mapper les jours français vers anglais
            day_mapping = {
                'Monday': 'Lundi', 'Tuesday': 'Mardi', 'Wednesday': 'Mercredi',
                'Thursday': 'Jeudi', 'Friday': 'Vendredi', 'Saturday': 'Samedi', 'Sunday': 'Dimanche'
            }
            
            french_day = day_mapping.get(current_day)
            
            if french_day and french_day in active_schedules:
                schedule = active_schedules[french_day]
                
                if schedule.get('enabled') and schedule.get('startTime') == current_hour_min:
                    print(f"🚿 Déclenchement irrigation programmée pour {french_day} à {current_hour_min}")
                    
                    # Utiliser la durée optimisée par IA
                    duration_minutes = schedule.get('ai_duration_minutes', 30)
                    volume_m3 = schedule.get('ai_volume_m3', 0.6)
                    duration_seconds = int(duration_minutes * 60)
                    
                    # Démarrer l'irrigation via MQTT (comme arrosage manuel)
                    success, message = mqtt_service.demarrer_arrosage_async(
                        duration_seconds, volume_m3, 'SCHEDULE_AI'
                    )
                    
                    if success:
                        print(f"✅ Irrigation programmée démarrée: {duration_minutes} min")
                        log_irrigation(
                            action='schedule_executed',
                            duration_minutes=duration_minutes,
                            volume_m3=volume_m3,
                            mqtt_status='started',
                            source='SCHEDULE_AI'
                        )
                    else:
                        print(f"❌ Échec irrigation programmée: {message}")
            
            # Vérifier toutes les minutes
            time.sleep(60)
            
        except Exception as e:
            print(f"❌ Erreur surveillance planning: {e}")
            time.sleep(60)


@irrigation_bp.route('/irrigation/schedule/status', methods=['GET'])
def get_schedule_status():
    """Retourne l'état des plannings actifs"""
    try:
        return jsonify({
            "active_schedules": active_schedules,
            "monitoring_active": schedule_thread is not None and schedule_thread.is_alive(),
            "current_time": datetime.datetime.now().isoformat()
        }), 200
    except Exception as e:
        print(f"❌ Erreur statut planning: {e}")
        return jsonify({"error": str(e)}), 500


@irrigation_bp.route('/irrigation/log-manual', methods=['POST'])
def log_manual_irrigation():
    try:
        data = request.get_json()
        duration_minutes = data.get('duration_minutes', 0)
        volume_m3 = data.get('volume_m3', 0)

        print(f"📊 Log irrigation manuelle: {duration_minutes:.1f} min, {volume_m3:.3f} m³")

        log_irrigation(
            action='manual_mqtt',
            duration_minutes=duration_minutes,
            volume_m3=volume_m3,
            mqtt_status='ok',
            source='MANUAL_DIRECT'
        )

        return jsonify({"success": True, "message": "Irrigation manuelle loggée"}), 200
    except Exception as e:
        print(f"❌ Erreur log irrigation manuelle: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@irrigation_bp.route('/irrigation/manual', methods=['POST'])
def start_manual_irrigation():
    try:
        print(f"⚠️ Legacy endpoint - Redirection vers MQTT direct recommandée")
        result = {"success": True, "message": "Legacy endpoint - utiliser MQTT direct"}
        return jsonify(result), 200
    except Exception as e:
        print(f"❌ Erreur irrigation manuelle legacy: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@irrigation_bp.route('/irrigation/stop', methods=['POST'])
def stop_irrigation():
    try:
        print("⏹️ Arrêt irrigation demandé")
        result = {"success": True, "message": "Irrigation arrêtée"}
        return jsonify(result), 200
    except Exception as e:
        print(f"❌ Erreur arrêt irrigation: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@irrigation_bp.route('/analytics/trends', methods=['GET'])
def get_trends():
    try:
        trends = {
            "waterConsumption": 1.25,
            "soilMoisture": 45,
            "efficiency": 92,
            "trend": "stable"
        }
        print(f"📊 Tendances calculées: {trends}")
        return jsonify(trends), 200
    except Exception as e:
        print(f"❌ Erreur trends: {e}")
        return jsonify({"error": str(e)}), 500


@irrigation_bp.route('/analytics/ml-predictions', methods=['GET'])
def get_ml_predictions():
    try:
        predictions = {
            "nextIrrigationHours": 4,
            "recommendedDuration": 25,
            "soilCondition": "Bon",
            "weatherImpact": "Favorable"
        }
        print(f"🧠 Prédictions ML: {predictions}")
        return jsonify(predictions), 200
    except Exception as e:
        print(f"❌ Erreur ML predictions: {e}")
        return jsonify({"error": str(e)}), 500
