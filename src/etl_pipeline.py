import os
import requests
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

print("🚀 Iniciando ETL Pipeline...")

# Conectar a la base de datos
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)

# API Key
API_KEY = os.getenv('API_FOOTBALL_KEY')

if not API_KEY:
    print("❌ Error: API_FOOTBALL_KEY no está configurada")
    exit(1)

print("✅ Conexión a base de datos establecida")

# Función para obtener partidos de hoy
def fetch_todays_matches():
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-rapidapi-key": API_KEY}
    today = datetime.now().strftime('%Y-%m-%d')
    
    params = {
        "date": today,
        "league": "140",  # LaLiga
        "season": "2025"
    }
    
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    
    if not data['response']:
        print("ℹ️ No hay partidos hoy")
        return pd.DataFrame()
    
    matches = []
    for match in data['response']:
        matches.append({
            'match_id': match['fixture']['id'],
            'season': 2025,
            'league_id': 140,
            'match_date': match['fixture']['date'][:10],
            'home_team_id': match['teams']['home']['id'],
            'away_team_id': match['teams']['away']['id'],
            'home_goals': match['goals']['home'] or 0,
            'away_goals': match['goals']['away'] or 0,
            'status': match['fixture']['status']['short']
        })
    
    return pd.DataFrame(matches)

# Ejecutar
df = fetch_todays_matches()

if not df.empty:
    # Guardar en la base de datos
    df.to_sql('matches', engine, if_exists='append', index=False)
    print(f"✅ Guardados {len(df)} partidos en la base de datos")
else:
    print("ℹ️ No se encontraron partidos para hoy")

print("✅ Pipeline completado")
