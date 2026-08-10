import os
import sys
import requests
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import subprocess
import time

print("=" * 60)
print("⚽ ETL PIPELINE - INICIANDO")
print("=" * 60)

load_dotenv()

API_KEY = os.getenv('FOOTBALL_DATA_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')

if not API_KEY:
    print("❌ ERROR: FOOTBALL_DATA_KEY no configurada")
    sys.exit(1)

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL no configurada")
    sys.exit(1)

print(f"✅ API_KEY configurada: {API_KEY[:10]}...")
print(f"✅ DATABASE_URL configurada: {DATABASE_URL[:20]}...")

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ Conexión a base de datos exitosa")
except Exception as e:
    print(f"❌ Error de conexión a BD: {e}")
    sys.exit(1)

def get_matches():
    url = "https://api.football-data.org/v4/matches"
    headers = {"X-Auth-Token": API_KEY}
    today = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\n📅 Fecha de hoy: {today}")
    
    competitions = [
        {"id": "PD", "name": "LaLiga"},
        {"id": "PL", "name": "Premier League"},
        {"id": "BL1", "name": "Bundesliga"},
        {"id": "SA", "name": "Serie A"},
        {"id": "FL1", "name": "Ligue 1"}
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
                print(f"  ⚠️ Límite excedido en {comp['name']}")
                time.sleep(60)
                response = requests.get(url, headers=headers, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"  ⚠️ Error {response.status_code} en {comp['name']}")
                continue
                
            data = response.json()
            matches = data.get('matches', [])
            
            if not matches:
                print(f"  ℹ️ No hay partidos en {comp['name']} hoy")
            else:
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
                
                print(f"  ✅ {len(matches)} partidos encontrados")
            
            if idx < len(competitions) - 1:
                print(f"  ⏳ Esperando 6 segundos...")
                time.sleep(6)
            
        except Exception as e:
            print(f"  ❌ Error en {comp['name']}: {e}")
    
    return pd.DataFrame(all_matches)

def main():
    try:
        print("\n" + "=" * 60)
        print("📊 ETL PIPELINE - EJECUTANDO")
        print("=" * 60)
        
        df = get_matches()
        
        if df.empty:
            print("\n✅ Pipeline completado - No hay partidos hoy")
            return
        
        print(f"\n💾 Guardando {len(df)} partidos...")
        df.to_sql('matches', engine, if_exists='append', index=False)
        
        print("\n📊 PARTIDOS DE HOY:")
        for _, row in df.iterrows():
            status_emoji = {
                'FT': '✅', 'NS': '⏰', '1H': '⏳',
                '2H': '⏳', 'HT': '⏸️', 'PST': '📅', 'CAN': '❌'
            }.get(row['status'], '⏰')
            print(f"  {status_emoji} {row['home_team_id']} vs {row['away_team_id']}")
        
        print(f"\n✅ {len(df)} partidos guardados correctamente")
        
        print("\n" + "=" * 60)
        print("🧠 EJECUTANDO MODELO DE PREDICCIÓN...")
        print("=" * 60)
        
        try:
            result = subprocess.run(
                ['python', 'src/model_trainer.py'],
                capture_output=True,
                text=True
            )
            print(result.stdout)
            if result.stderr:
                print(f"⚠️ Errores: {result.stderr}")
        except Exception as e:
            print(f"❌ Error ejecutando modelo: {e}")
        
    except Exception as e:
        print(f"\n❌ Error en el pipeline: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
    print("\n" + "=" * 60)
    print("✅ PIPELINE COMPLETADO EXITOSAMENTE")
    print("=" * 60)
