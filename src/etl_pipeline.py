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
print("⚽ ETL PIPELINE - INICIANDO (API-Football)")
print("=" * 60)

load_dotenv()

API_KEY = os.getenv('API_FOOTBALL_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')

if not API_KEY:
    print("❌ ERROR: API_FOOTBALL_KEY no configurada")
    print("ℹ️ Configura la variable API_FOOTBALL_KEY")
    print("   Ve a https://www.api-football.com y obtén tu API Key")
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
    """Obtiene partidos de hoy desde API-Football"""
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-rapidapi-key": API_KEY}
    today = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\n📅 Fecha de hoy: {today}")
    
    # 🔥 LIGAS DISPONIBLES EN EL PLAN GRATUITO
    leagues = [
        {"id": 39, "name": "Premier League"},
        {"id": 140, "name": "LaLiga"},
        {"id": 78, "name": "Bundesliga"},
        {"id": 135, "name": "Serie A"},
        {"id": 61, "name": "Ligue 1"},
        {"id": 2, "name": "Champions League"},
        {"id": 3, "name": "Europa League"},
        {"id": 4, "name": "Conference League"},
    ]
    
    all_matches = []
    
    for idx, league in enumerate(leagues):
        try:
            print(f"\n🔍 Buscando en {league['name']}...")
            
            params = {
                "league": league["id"],
                "season": "2025",
                "date": today
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            if response.status_code == 429:
                print(f"  ⚠️ Límite excedido en {league['name']}")
                time.sleep(60)
                continue
            
            if response.status_code != 200:
                print(f"  ⚠️ Error {response.status_code} en {league['name']}")
                continue
                
            data = response.json()
            matches = data.get('response', [])
            
            if not matches:
                print(f"  ℹ️ No hay partidos en {league['name']} hoy")
            else:
                status_map = {
                    'NS': 'NS', '1H': '1H', '2H': '2H',
                    'HT': 'HT', 'FT': 'FT', 'PST': 'PST',
                    'CANC': 'CANC'
                }
                
                for match in matches:
                    fixture = match.get('fixture', {})
                    home_team = match.get('teams', {}).get('home', {})
                    away_team = match.get('teams', {}).get('away', {})
                    goals = match.get('goals', {})
                    
                    match_data = {
                        'match_id': fixture.get('id'),
                        'season': 2025,
                        'league_id': league["id"],
                        'match_date': fixture.get('date', today)[:10],
                        'home_team_id': home_team.get('id'),
                        'away_team_id': away_team.get('id'),
                        'home_goals': goals.get('home') if goals.get('home') is not None else 0,
                        'away_goals': goals.get('away') if goals.get('away') is not None else 0,
                        'status': status_map.get(fixture.get('status', {}).get('short', 'NS'), 'NS')
                    }
                    
                    if match_data['home_team_id'] and match_data['away_team_id']:
                        all_matches.append(match_data)
                
                print(f"  ✅ {len(matches)} partidos encontrados en {league['name']}")
            
            # Esperar 6 segundos para no exceder el límite de la API
            if idx < len(leagues) - 1:
                print(f"  ⏳ Esperando 6 segundos...")
                time.sleep(6)
            
        except Exception as e:
            print(f"  ❌ Error en {league['name']}: {e}")
    
    if not all_matches:
        print("\nℹ️ No se encontraron partidos en ninguna liga")
        return pd.DataFrame()
    
    print(f"\n✅ Total partidos encontrados: {len(all_matches)}")
    return pd.DataFrame(all_matches)

def update_teams(matches_df):
    """Guarda los equipos en la base de datos"""
    if matches_df.empty:
        return
    
    team_ids = set(matches_df['home_team_id'].tolist() + matches_df['away_team_id'].tolist())
    print(f"\n🏢 Guardando {len(team_ids)} equipos...")
    
    for team_id in team_ids:
        try:
            query = text("SELECT COUNT(*) FROM teams WHERE team_id = :team_id")
            with engine.connect() as conn:
                count = conn.execute(query, {"team_id": team_id}).scalar()
            
            if count > 0:
                continue
                
            url = "https://v3.football.api-sports.io/teams"
            headers = {"x-rapidapi-key": API_KEY}
            params = {"id": team_id}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json()
            
            if data.get('response'):
                team = data['response'][0]['team']
                venue = data['response'][0].get('venue', {})
                
                new_team = pd.DataFrame([{
                    'team_id': team.get('id'),
                    'team_name': team.get('name', 'Unknown'),
                    'market_value': 0,
                    'stadium_capacity': venue.get('capacity', 0),
                    'avg_age': 0,
                    'country': venue.get('country', 'Unknown')
                }])
                
                new_team.to_sql('teams', engine, if_exists='append', index=False)
                print(f"  ✅ {team.get('name')}")
                
        except Exception as e:
            print(f"  ⚠️ Error con equipo {team_id}: {e}")

def main():
    try:
        print("\n" + "=" * 60)
        print("📊 ETL PIPELINE - EJECUTANDO")
        print("=" * 60)
        
        df = get_matches()
        
        if df.empty:
            print("\n✅ Pipeline completado - No hay partidos hoy")
            return
        
        update_teams(df)
        
        print(f"\n💾 Guardando {len(df)} partidos en la base de datos...")
        df.to_sql('matches', engine, if_exists='append', index=False)
        
        print("\n📊 PARTIDOS DE HOY:")
        for _, row in df.iterrows():
            status_emoji = {
                'FT': '✅', 'NS': '⏰', '1H': '⏳',
                '2H': '⏳', 'HT': '⏸️', 'PST': '📅', 'CANC': '❌'
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
