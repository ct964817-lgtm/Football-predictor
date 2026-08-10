import os
import requests
import pandas as pd
import json
from datetime import datetime
from sqlalchemy import create_engine
import pickle

print("=" * 60)
print("📱 TELEGRAM ALERTS - INICIANDO")
print("=" * 60)

# Configuración
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
DATABASE_URL = os.getenv('DATABASE_URL')

if not BOT_TOKEN or not CHAT_ID:
    print("❌ TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados")
    exit(0)

engine = create_engine(DATABASE_URL)

def send_telegram_message(message):
    """Envía un mensaje a Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error enviando mensaje: {e}")
        return False

def find_value_bets():
    """Encuentra Value Bets comparando probabilidades del modelo con cuotas del mercado"""
    
    # Cargar predicciones de hoy
    query = """
    SELECT 
        p.*,
        t1.team_name as home_name,
        t2.team_name as away_name
    FROM predictions p
    JOIN teams t1 ON p.home_team_id = t1.team_id
    JOIN teams t2 ON p.away_team_id = t2.team_id
    WHERE p.match_date >= CURRENT_DATE
    """
    
    df = pd.read_sql(query, engine)
    
    if df.empty:
        return []
    
    value_bets = []
    
    for _, row in df.iterrows():
        # Cuotas justas (sin margen)
        fair_odds = {
            'home': 1 / row['prob_home'],
            'draw': 1 / row['prob_draw'],
            'away': 1 / row['prob_away']
        }
        
        # Cuotas reales (simuladas - en producción vendrían de API)
        # Aquí puedes conectar con una API de odds
        real_odds = {
            'home': fair_odds['home'] * 0.92,  # Simulando margen de casa
            'draw': fair_odds['draw'] * 0.92,
            'away': fair_odds['away'] * 0.92
        }
        
        # Detectar Value Bets
        for market in ['home', 'draw', 'away']:
            value = (row[f'prob_{market}'] * real_odds[market]) - 1
            
            if value > 0.05:  # 5% de ventaja
                value_bets.append({
                    'match': f"{row['home_name']} vs {row['away_name']}",
                    'market': market.capitalize(),
                    'fair_odds': fair_odds[market],
                    'real_odds': real_odds[market],
                    'value': value,
                    'probability': row[f'prob_{market}'],
                    'match_id': row['match_id'],
                    'date': row['match_date']
                })
    
    return value_bets

def format_value_bet_message(value_bets):
    """Formatea los Value Bets para enviar por Telegram"""
    if not value_bets:
        return "🔍 No se encontraron Value Bets con ventaja > 5% hoy."
    
    message = "🎯 <b>VALUE BETS ENCONTRADAS</b> 🎯\n"
    message += f"📅 {datetime.now().strftime('%d/%m/%Y')}\n"
    message += "━" * 30 + "\n\n"
    
    for bet in value_bets[:5]:  # Limitar a 5 por mensaje
        emoji = {
            'Home': '🏠',
            'Draw': '🤝',
            'Away': '✈️'
        }.get(bet['market'], '⚽')
        
        message += f"{emoji} <b>{bet['match']}</b>\n"
        message += f"📊 Mercado: {bet['market']}\n"
        message += f"📈 Probabilidad: {bet['probability']:.1%}\n"
        message += f"💰 Cuota justa: {bet['fair_odds']:.2f}\n"
        message += f"🏦 Cuota real: {bet['real_odds']:.2f}\n"
        
        color = "🟢" if bet['value'] > 0.15 else "🟡" if bet['value'] > 0.10 else "🟠"
        message += f"{color} <b>Ventaja: {bet['value']:.1%}</b>\n"
        
        # Stake sugerido
        if bet['value'] > 0.20:
            stake = "5% (Alto)"
        elif bet['value'] > 0.10:
            stake = "3% (Medio)"
        else:
            stake = "1% (Bajo)"
        
        message += f"📌 Stake sugerido: {stake}\n\n"
    
    message += "━" * 30 + "\n"
    message += f"📊 Total Value Bets: {len(value_bets)}\n"
    
    return message

def main():
    """Función principal"""
    print("📊 Buscando Value Bets...")
    value_bets = find_value_bets()
    
    if value_bets:
        print(f"✅ Encontradas {len(value_bets)} Value Bets")
        message = format_value_bet_message(value_bets)
        
        if send_telegram_message(message):
            print("✅ Mensaje enviado a Telegram")
            
            # Guardar en base de datos
            df = pd.DataFrame(value_bets)
            df['created_at'] = datetime.now()
            df.to_sql('value_bets', engine, if_exists='append', index=False)
            print("💾 Value Bets guardadas en base de datos")
        else:
            print("❌ Error enviando mensaje a Telegram")
    else:
        print("ℹ️ No se encontraron Value Bets")
        # Enviar mensaje informativo
        send_telegram_message("🔍 No se encontraron Value Bets con ventaja > 5% hoy.")

if _name_ == "_main_":
    main()
    print("\n" + "=" * 60)
    print("✅ ALERTAS COMPLETADAS")
    print("=" * 60)
