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

# Función para obtener partidos desde Football-Data.org
def get_matches():
    """Obtiene partidos de hoy desde Football-Data.org"""
    url = "https://api.football-data.org/v4/matches"
    headers = {"X-Auth-Token": API_KEY}
    today = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\n📅 Fecha de hoy: {today}")
    
    # Ligas (ID de Football-Data.org)
    competitions = [
        {"id": "PD", "name": "LaLiga"},
        {"id": "PL", "name": "Premier League"},
        {"id": "BL1", "name": "Bundesliga"},
        {"id": "SA", "name": "Serie A"},
        {"id": "FL1", "name": "Ligue 1"}
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
            
            # Mapear resultados de Football-Data.org
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

def main():
    """Función principal"""
    try:
        print("\n" + "=" * 60)
        print("📊 ETL PIPELINE - EJECUTANDO")
        print("=" * 60)
        
        # Obtener partidos
        df = get_matches()
        
        if df.empty:
            print("\n✅ Pipeline completado - No hay partidos hoy")
            return  # <-- SALIR AQUÍ SI NO HAY PARTIDOS
        
        # Guardar en base de datos
        print(f"\n💾 Guardando {len(df)} partidos en la base de datos...")
        
        # Crear tabla si no existe (simple)
        df.head(0).to_sql('matches', engine, if_exists='replace', index=False)
        
        # Guardar datos
        df.to_sql('matches', engine, if_exists='append', index=False)
        
        print("\n📊 PARTIDOS DE HOY:")
        for _, row in df.iterrows():
            status_emoji = {
                'FT': '✅',
                'NS': '⏰',
                '1H': '⏳',
                '2H': '⏳',
                'HT': '⏸️',
                'PST': '📅',
                'CAN': '❌'
            }.get(row['status'], '⏰')
            print(f"  {status_emoji} ID:{row['match_id']} - {row['home_team_id']} vs {row['away_team_id']}")
        
        print(f"\n✅ {len(df)} partidos guardados correctamente")
        
        # --- EJECUTAR MODELO DE PREDICCIÓN ---
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
        
        # --- ENVIAR ALERTAS DE TELEGRAM ---
        print("\n" + "=" * 60)
        print("📱 ENVIANDO ALERTAS DE TELEGRAM...")
        print("=" * 60)
        
        try:
            result = subprocess.run(
                ['python', 'src/telegram_alerts.py'], 
                capture_output=True, 
                text=True
            )
            print(result.stdout)
            if result.stderr:
                print(f"⚠️ Errores: {result.stderr}")
        except Exception as e:
            print(f"❌ Error enviando alertas: {e}")
        
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
