import os
import sys
import requests
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

print("=" * 60)
print("⚽ ETL PIPELINE - INICIANDO")
print("=" * 60)

# Cargar variables de entorno
load_dotenv()

# Obtener variables
API_KEY = os.getenv('API_FOOTBALL_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')

# Verificar API Key
if not API_KEY:
    print("❌ ERROR: API_FOOTBALL_KEY no configurada")
    print("ℹ️ Configura la variable API_FOOTBALL_KEY")
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

# Función para obtener partidos
def get_matches():
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-rapidapi-key": API_KEY}
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Liga: 140 = LaLiga, 39 = Premier League
    leagues = [
        {"id": 140, "name": "LaLiga"},
        {"id": 39, "name": "Premier League"}
    ]
    
    all_matches = []
    
    for league in leagues:
        print(f"\n🔍 Buscando en {league['name']}...")
        
        try:
            params = {
                "date": today,
                "league": league["id"],
                "season": "2025"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"  ⚠️ Error {response.status_code} en {league['name']}")
                continue
            
            data = response.json()
            
            if not data.get('response'):
                print(f"  ℹ️ No hay partidos en {league['name']} hoy")
                continue
            
            for match in data['response']:
                fixture = match.get('fixture', {})
                home = match.get('teams', {}).get('home', {})
                away = match.get('teams', {}).get('away', {})
                goals = match.get('goals', {})
                
                match_data = {
                    'match_id': fixture.get('id'),
                    'season': 2025,
                    'league_id': league["id"],
                    'match_date': fixture.get('date', today)[:10],
                    'home_team_id': home.get('id'),
                    'away_team_id': away.get('id'),
                    'home_goals': goals.get('home') or 0,
                    'away_goals': goals.get('away') or 0,
                    'status': fixture.get('status', {}).get('short', 'NS')
                }
                
                if match_data['home_team_id'] and match_data['away_team_id']:
                    all_matches.append(match_data)
            
            print(f"  ✅ {len(data['response'])} partidos encontrados")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    return pd.DataFrame(all_matches)

# Función principal
def main():
    print("\n📅 Fecha de hoy:", datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    # Obtener partidos
    df = get_matches()
    
    if df.empty:
        print("\nℹ️ No se encontraron partidos hoy")
        print("\n✅ Pipeline completado (sin datos)")
        return
    
    # Guardar en base de datos
    print(f"\n💾 Guardando {len(df)} partidos...")
    
    try:
        # Crear tabla si no existe (simple)
        df.head(0).to_sql('matches', engine, if_exists='replace', index=False)
        
        # Guardar datos
        df.to_sql('matches', engine, if_exists='append', index=False)
        print(f"✅ {len(df)} partidos guardados correctamente")
        
        # Mostrar resumen
        print("\n📊 PARTIDOS DE HOY:")
        for _, row in df.iterrows():
            print(f"  ⚽ {row['home_team_id']} vs {row['away_team_id']} - {row['status']}")
            
    except Exception as e:
        print(f"❌ Error guardando datos: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ PIPELINE COMPLETADO EXITOSAMENTE")
    print("=" * 60)

if __name__ == "__main__":
    main()
