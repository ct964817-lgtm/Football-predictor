import os
import sys
import requests
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import subprocess

print("=" * 60)
print("⚽ ETL PIPELINE - INICIANDO")
print("=" * 60)

# Cargar variables de entorno
load_dotenv()

# Obtener variables
API_KEY = os.getenv('FOOTBALL_DATA_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')

# Verificar API Key
if not API_KEY:
    print("❌ ERROR: FOOTBALL_DATA_KEY no configurada")
    print("ℹ️ Configura la variable FOOTBALL_DATA_KEY")
    print("   Ve a https://www.football-data.org y obtén tu API Key")
    sys.exit(1)

# Verificar Database
if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL no configurada")
    print("ℹ️ Configura la variable DATABASE_URL")
    sys.exit(1)

print(f"✅ API_KEY configurada: {API_KEY[:10]}...")
print(f"✅ DATABASE_URL configurada: {DATABASE_URL[:20]}...")

# Probar conexión a la base de datos
try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ Conexión a base de datos exitosa")
except Exception as e:
    print(f"❌ Error de conexión a BD: {e}")
    sys.exit(1)

# ============================================
# FUNCIÓN PRINCIPAL: get_matches()
# ============================================
def get_matches():
    """Obtiene partidos de hoy desde Football-Data.org"""
    url = "https://api.football-data.org/v4/matches"
    headers = {"X-Auth-Token": API_KEY}
    today = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\n📅 Fecha de hoy: {today}")
    
    # 🔥 LISTA COMPLETA DE LIGAS (25 ligas)
    competitions = [
        # 🌟 TOP 5 EUROPEAS
        {"id": "PD", "name": "LaLiga"},
        {"id": "PL", "name": "Premier League"},
        {"id": "BL1", "name": "Bundesliga"},
        {"id": "SA", "name": "Serie A"},
        {"id": "FL1", "name": "Ligue 1"},
        
        # 🌟 SEGUNDAS DIVISIONES
        {"id": "SD", "name": "LaLiga 2"},
        {"id": "ELC", "name": "Championship"},
        {"id": "BL2", "name": "Bundesliga 2"},
        
        # 🌟 OTRAS LIGAS EUROPEAS
        {"id": "PPL", "name": "Primeira Liga"},
        {"id": "DED", "name": "Eredivisie"},
        {"id": "BPL", "name": "Pro League"},
        {"id": "GSL", "name": "Super League"},
        {"id": "SUL", "name": "Super Lig"},
        {"id": "CDL", "name": "Liga Checa"},
        {"id": "DPL", "name": "Liga Danesa"},
        {"id": "NSL", "name": "Liga Noruega"},
        {"id": "SWL", "name": "Liga Sueca"},
        
        # 🌟 AMÉRICA
        {"id": "MLS", "name": "MLS"},
        {"id": "BSA", "name": "Brasileirão"},
        {"id": "LFA", "name": "Liga Argentina"},
        {"id": "LMS", "name": "Liga MX"},
        
        # 🌟 ASIA Y OCEANÍA
        {"id": "AUL", "name": "A-League"},
        {"id": "JFL", "name": "J-League"},
        {"id": "KFL", "name": "K-League"},
    ]
    
    all_matches = []
    
    for comp in competitions:
        try:
            print(f"\n🔍 Buscando en {comp['name']}...")
            
            params = {
                "dateFrom": today,
                "dateTo": today,
                "competitions": comp["id"]
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"  ⚠️ Error {response.status_code} en {comp['name']}")
                if response.status_code == 403:
                    print("  ⚠️ Posible límite de peticiones excedido (10/minuto)")
                continue
                
            data = response.json()
            matches = data.get('matches', [])
            
            if not matches:
                print(f"  ℹ️ No hay partidos en {comp['name']} hoy")
                continue
            
            # Mapear estados
            status_map = {
                'SCHEDULED': 'NS',
                'LIVE': '1H',
                'IN_PLAY': '1H',
                'PAUSED': 'HT',
                'FINISHED': 'FT',
                'POSTPONED': 'PST',
                'CANCELLED': 'CAN'
            }
            
            for match in matches:
                home_team = match.get('homeTeam', {})
                away_team = match.get('awayTeam', {})
                score = match.get('score', {}).get('fullTime', {})
                
                match_data = {
                    'match_id': match.get('id'),
                    'season': 2025,
                    'league_id': comp["id"],
                    'match_date': match.get('utcDate', today)[:10],
                    'home_team_id': home_team.get('id'),
                    'away_team_id': away_team.get('id'),
                    'home_goals': score.get('home') if score.get('home') is not None else 0,
                    'away_goals': score.get('away') if score.get('away') is not None else 0,
                    'status': status_map.get(match.get('status', ''), 'NS')
                }
                
                if match_data['home_team_id'] and match_data['away_team_id']:
                    all_matches.append(match_data)
            
            print(f"  ✅ {len(matches)} partidos encontrados en {comp['name']}")
            
        except requests.exceptions.Timeout:
            print(f"  ⚠️ Timeout en {comp['name']}")
        except Exception as e:
            print(f"  ❌ Error en {comp['name']}: {e}")
    
    if not all_matches:
        print("\nℹ️ No se encontraron partidos en ninguna liga")
        return pd.DataFrame()
    
    print(f"\n✅ Total partidos encontrados: {len(all_matches)}")
    return pd.DataFrame(all_matches)

# ============================================
# FUNCIÓN PRINCIPAL
# ============================================
def main():
    """Función principal"""
    try:
        print("\n" + "=" * 60)
        print("📊 ETL PIPELINE - EJECUTANDO")
        print("=" * 60)
         
import time  # <-- Asegúrate de tener esta importación al inicio del archivo

def get_matches():
    """Obtiene partidos de hoy desde Football-Data.org"""
    url = "https://api.football-data.org/v4/matches"
    headers = {"X-Auth-Token": API_KEY}
    today = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\n📅 Fecha de hoy: {today}")
    
    # 🔥 LISTA COMPLETA DE LIGAS (25 ligas)
    competitions = [
        # 🌟 TOP 5 EUROPEAS
        {"id": "PD", "name": "LaLiga"},
        {"id": "PL", "name": "Premier League"},
        {"id": "BL1", "name": "Bundesliga"},
        {"id": "SA", "name": "Serie A"},
        {"id": "FL1", "name": "Ligue 1"},
        
        # 🌟 SEGUNDAS DIVISIONES
        {"id": "SD", "name": "LaLiga 2"},
        {"id": "ELC", "name": "Championship"},
        {"id": "BL2", "name": "Bundesliga 2"},
        {"id": "SB", "name": "Serie B"},
        
        # 🌟 OTRAS LIGAS EUROPEAS
        {"id": "PPL", "name": "Primeira Liga"},
        {"id": "DED", "name": "Eredivisie"},
        {"id": "BPL", "name": "Pro League"},
        {"id": "GSL", "name": "Super League"},
        {"id": "SUL", "name": "Super Lig"},
        {"id": "CDL", "name": "Liga Checa"},
        {"id": "DPL", "name": "Liga Danesa"},
        {"id": "NSL", "name": "Liga Noruega"},
        {"id": "SWL", "name": "Liga Sueca"},
        
        # 🌟 AMÉRICA
        {"id": "MLS", "name": "MLS"},
        {"id": "BSA", "name": "Brasileirão"},
        {"id": "LFA", "name": "Liga Argentina"},
        {"id": "LMS", "name": "Liga MX"},
        
        # 🌟 ASIA Y OCEANÍA
        {"id": "AUL", "name": "A-League"},
        {"id": "JFL", "name": "J-League"},
        {"id": "KFL", "name": "K-League"},
    ]
    
    all_matches = []
    
    for idx, comp in enumerate(competitions):
        try:
            print(f"\n🔍 Buscando en {comp['name']}...")
            
            params = {
                "dateFrom": today,
                "dateTo": today,
                "competitions": comp["id"]
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            if response.status_code == 429:
                print(f"  ⚠️ Límite de peticiones excedido en {comp['name']}")
                print(f"  ⏳ Esperando 60 segundos...")
                time.sleep(60)  # Esperar 1 minuto si hay error 429
                # Reintentar una vez
                response = requests.get(url, headers=headers, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"  ⚠️ Error {response.status_code} en {comp['name']}")
                continue
                
            data = response.json()
            matches = data.get('matches', [])
            
            if not matches:
                print(f"  ℹ️ No hay partidos en {comp['name']} hoy")
            else:
                # Mapear estados
                status_map = {
                    'SCHEDULED': 'NS',
                    'LIVE': '1H',
                    'IN_PLAY': '1H',
                    'PAUSED': 'HT',
                    'FINISHED': 'FT',
                    'POSTPONED': 'PST',
                    'CANCELLED': 'CAN'
                }
                
                for match in matches:
                    home_team = match.get('homeTeam', {})
                    away_team = match.get('awayTeam', {})
                    score = match.get('score', {}).get('fullTime', {})
                    
                    match_data = {
                        'match_id': match.get('id'),
                        'season': 2025,
                        'league_id': comp["id"],
                        'match_date': match.get('utcDate', today)[:10],
                        'home_team_id': home_team.get('id'),
                        'away_team_id': away_team.get('id'),
                        'home_goals': score.get('home') if score.get('home') is not None else 0,
                        'away_goals': score.get('away') if score.get('away') is not None else 0,
                        'status': status_map.get(match.get('status', ''), 'NS')
                    }
                    
                    if match_data['home_team_id'] and match_data['away_team_id']:
                        all_matches.append(match_data)
                
                print(f"  ✅ {len(matches)} partidos encontrados en {comp['name']}")
            
            # ⏰ ESPERAR 6 SEGUNDOS ENTRE LIGAS (10 peticiones/minuto)
            if idx < len(competitions) - 1:  # No esperar después de la última
                print(f"  ⏳ Esperando 6 segundos para evitar límite de API...")
                time.sleep(6)
            
        except requests.exceptions.Timeout:
            print(f"  ⚠️ Timeout en {comp['name']}")
        except Exception as e:
            print(f"  ❌ Error en {comp['name']}: {e}")
    
    if not all_matches:
        print("\nℹ️ No se encontraron partidos en ninguna liga")
        return pd.DataFrame()
    
    print(f"\n✅ Total partidos encontrados: {len(all_matches)}")
    return pd.DataFrame(all_matches)
