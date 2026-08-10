import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sklearn.linear_model import PoissonRegressor
from sklearn.model_selection import train_test_split
from datetime import datetime, timedelta
import pickle
import json

print("=" * 60)
print("🤖 MODELO DE PREDICCIÓN - INICIANDO")
print("=" * 60)

# Conectar a la base de datos
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)

# Cargar datos históricos
print("📊 Cargando datos históricos...")

query = """
SELECT 
    m.match_id,
    m.match_date,
    m.home_team_id,
    m.away_team_id,
    m.home_goals,
    m.away_goals,
    m.home_shots,
    m.away_shots,
    m.home_shots_on_target,
    m.away_shots_on_target,
    m.home_possession,
    m.away_possession,
    t1.team_name as home_name,
    t2.team_name as away_name,
    e1.elo_general as home_elo,
    e2.elo_general as away_elo
FROM matches m
JOIN teams t1 ON m.home_team_id = t1.team_id
JOIN teams t2 ON m.away_team_id = t2.team_id
LEFT JOIN elo_ratings e1 ON m.home_team_id = e1.team_id AND m.match_date = e1.match_date
LEFT JOIN elo_ratings e2 ON m.away_team_id = e2.team_id AND m.match_date = e2.match_date
WHERE m.home_goals IS NOT NULL AND m.away_goals IS NOT NULL
ORDER BY m.match_date
"""

df = pd.read_sql(query, engine)

if df.empty:
    print("❌ No hay datos históricos suficientes para entrenar")
    print("ℹ️ Espera a que haya partidos jugados")
    exit(0)

print(f"✅ {len(df)} partidos cargados")

# Preparar features
print("🔧 Preparando features...")

# Features para goles local
features_home = [
    'home_elo', 'away_elo', 'home_shots', 'home_shots_on_target', 'home_possession'
]

# Features para goles visitante
features_away = [
    'home_elo', 'away_elo', 'away_shots', 'away_shots_on_target', 'away_possession'
]

# Limpiar datos
df = df.fillna(0)
df = df.replace([np.inf, -np.inf], 0)

# Entrenar modelo para goles locales
print("🏋️ Entrenando modelo para goles locales...")

X_home = df[features_home]
y_home = df['home_goals']

model_home = PoissonRegressor(alpha=0.1, max_iter=1000)
model_home.fit(X_home, y_home)

# Entrenar modelo para goles visitantes
print("🏋️ Entrenando modelo para goles visitantes...")

X_away = df[features_away]
y_away = df['away_goals']

model_away = PoissonRegressor(alpha=0.1, max_iter=1000)
model_away.fit(X_away, y_away)

# Guardar modelos
print("💾 Guardando modelos...")

os.makedirs('models', exist_ok=True)

with open('models/poisson_home.pkl', 'wb') as f:
    pickle.dump(model_home, f)

with open('models/poisson_away.pkl', 'wb') as f:
    pickle.dump(model_away, f)

# Guardar features usados
with open('models/features.json', 'w') as f:
    json.dump({
        'features_home': features_home,
        'features_away': features_away
    }, f)

# Calcular precisión
print("📊 Calculando precisión...")

# Predicciones en el mismo dataset
df['pred_home'] = model_home.predict(X_home)
df['pred_away'] = model_away.predict(X_away)

df['pred_result'] = np.where(
    df['pred_home'] > df['pred_away'], 'H',
    np.where(df['pred_home'] < df['pred_away'], 'A', 'D')
)
df['real_result'] = np.where(
    df['home_goals'] > df['away_goals'], 'H',
    np.where(df['home_goals'] < df['away_goals'], 'A', 'D')
)

accuracy = (df['pred_result'] == df['real_result']).mean()
print(f"✅ Precisión del modelo: {accuracy:.2%}")

print("\n" + "=" * 60)
print("✅ MODELO ENTRENADO EXITOSAMENTE")
print("=" * 60)
