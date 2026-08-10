import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
import json
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de página
st.set_page_config(
    page_title="⚽ Football Predictor Pro",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1a2e;
        text-align: center;
        padding: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .metric-card-blue {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .metric-card-green {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        padding: 1rem;
        border-radius: 10px;
        color: #1a1a2e;
        text-align: center;
    }
    .metric-card-orange {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        padding: 1rem;
        border-radius: 10px;
        color: #1a1a2e;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Conectar a la base de datos
@st.cache_resource
def init_db():
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return create_engine(db_url)
    return None

engine = init_db()

# Funciones de carga de datos
@st.cache_data(ttl=3600)
def load_todays_matches():
    if not engine:
        return pd.DataFrame()
    try:
        query = """
        SELECT 
            m.*,
            t1.team_name as home_name,
            t2.team_name as away_name
        FROM matches m
        LEFT JOIN teams t1 ON m.home_team_id = t1.team_id
        LEFT JOIN teams t2 ON m.away_team_id = t2.team_id
        WHERE m.match_date = CURRENT_DATE
        ORDER BY m.match_date
        """
        return pd.read_sql(query, engine)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_historical_stats():
    if not engine:
        return pd.DataFrame()
    try:
        query = """
        SELECT 
            match_date,
            home_goals,
            away_goals,
            home_goals + away_goals as total_goals
        FROM matches
        WHERE match_date >= CURRENT_DATE - INTERVAL '90 days'
        AND home_goals IS NOT NULL
        """
        return pd.read_sql(query, engine)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_team_stats():
    if not engine:
        return pd.DataFrame()
    try:
        query = """
        SELECT 
            t1.team_name,
            COUNT(*) as matches_played,
            SUM(CASE WHEN m.home_goals > m.away_goals AND m.home_team_id = t1.team_id THEN 1 
                     WHEN m.away_goals > m.home_goals AND m.away_team_id = t1.team_id THEN 1 
                     ELSE 0 END) as wins,
            AVG(CASE WHEN m.home_team_id = t1.team_id THEN m.home_goals 
                     ELSE m.away_goals END) as avg_goals_for,
            AVG(CASE WHEN m.home_team_id = t1.team_id THEN m.away_goals 
                     ELSE m.home_goals END) as avg_goals_against
        FROM matches m
        JOIN teams t1 ON m.home_team_id = t1.team_id OR m.away_team_id = t1.team_id
        WHERE m.match_date >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY t1.team_name
        ORDER BY wins DESC
        LIMIT 10
        """
        return pd.read_sql(query, engine)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_predictions():
    if not engine:
        return pd.DataFrame()
    try:
        query = """
        SELECT 
            p.*,
            t1.team_name as home_name,
            t2.team_name as away_name
        FROM predictions p
        JOIN teams t1 ON p.home_team_id = t1.team_id
        JOIN teams t2 ON p.away_team_id = t2.team_id
        WHERE p.match_date >= CURRENT_DATE
        ORDER BY p.match_date
        """
        return pd.read_sql(query, engine)
    except:
        return pd.DataFrame()

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/football2.png", width=80)
    st.title("⚽ Predictor Pro")
    st.markdown("---")
    
    st.subheader("📅 Filtros")
    date_range = st.date_input(
        "Período",
        value=(datetime.now() - timedelta(days=30), datetime.now()),
        max_value=datetime.now()
    )
    
    st.markdown("---")
    st.subheader("📊 Estadísticas Rápidas")
    
    # Métricas del día
    df_today = load_todays_matches()
    st.metric("📋 Partidos Hoy", len(df_today))
    
    df_hist = load_historical_stats()
    if not df_hist.empty:
        avg_goals = df_hist['total_goals'].mean()
        st.metric("⚽ Promedio Goles", f"{avg_goals:.2f}")
    
    st.markdown("---")
    st.caption(f"🔄 Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# --- MAIN CONTENT ---
st.markdown('<p class="main-header">⚽ Football Predictor Pro</p>', unsafe_allow_html=True)
st.markdown("---")

# Tabs principales
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Panel Principal",
    "🔮 Predicciones",
    "📈 Análisis Histórico",
    "📋 Partidos Hoy"
])

# --- TAB 1: PANEL PRINCIPAL ---
with tab1:
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    df_today = load_todays_matches()
    df_hist = load_historical_stats()
    df_stats = load_team_stats()
    df_pred = load_predictions()
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📋 {len(df_today)}</h3>
            <p>Partidos Hoy</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if not df_hist.empty:
            avg_goals = df_hist['total_goals'].mean()
            st.markdown(f"""
            <div class="metric-card-blue">
                <h3>⚽ {avg_goals:.2f}</h3>
                <p>Promedio Goles</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col3:
        if not df_stats.empty:
            total_goals = df_stats['avg_goals_for'].sum()
            st.markdown(f"""
            <div class="metric-card-green">
                <h3>🏆 {len(df_stats)}</h3>
                <p>Equipos Activos</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col4:
        if not df_pred.empty:
            st.markdown(f"""
            <div class="metric-card-orange">
                <h3>🔮 {len(df_pred)}</h3>
                <p>Predicciones</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Gráficos principales
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Distribución de Resultados")
        if not df_hist.empty:
            # Simular distribución de resultados
            results = {
                'Local Gana': (df_hist['home_goals'] > df_hist['away_goals']).sum(),
                'Empate': (df_hist['home_goals'] == df_hist['away_goals']).sum(),
                'Visita Gana': (df_hist['home_goals'] < df_hist['away_goals']).sum()
            }
            
            fig = go.Figure(go.Pie(
                labels=list(results.keys()),
                values=list(results.values()),
                marker=dict(colors=['#2ecc71', '#f1c40f', '#e74c3c']),
                hole=0.4,
                textinfo='label+percent'
            ))
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📈 Evolución de Goles")
        if not df_hist.empty:
            df_hist_sorted = df_hist.sort_values('match_date').tail(30)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_hist_sorted['match_date'],
                y=df_hist_sorted['total_goals'],
                mode='lines+markers',
                name='Goles Totales',
                line=dict(color='#3498db', width=2),
                fill='tozeroy',
                fillcolor='rgba(52, 152, 219, 0.2)'
            ))
            fig.update_layout(
                height=400,
                xaxis_title="Fecha",
                yaxis_title="Goles",
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Top equipos
    st.subheader("🏆 Top Equipos (Últimos 30 días)")
    if not df_stats.empty:
        fig = go.Figure(go.Bar(
            x=df_stats['team_name'],
            y=df_stats['wins'],
            marker_color=['#2ecc71' if i < 3 else '#3498db' for i in range(len(df_stats))],
            text=df_stats['wins'],
            textposition='outside'
        ))
        fig.update_layout(
            height=400,
            xaxis_title="Equipo",
            yaxis_title="Victorias",
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: PREDICCIONES ---
with tab2:
    st.subheader("🔮 Predicciones de Partidos")
    
    if not df_pred.empty:
        for _, pred in df_pred.iterrows():
            with st.expander(f"⚽ {pred.get('home_name', 'Local')} vs {pred.get('away_name', 'Visita')} - {pred.get('match_date', '')}"):
                col1, col2, col3 = st.columns([2, 1, 2])
                
                with col1:
                    st.metric(
                        "Goles Esperados",
                        f"{pred.get('lambda_home', 0):.2f} - {pred.get('lambda_away', 0):.2f}"
                    )
                    st.metric(
                        "Marcador Más Probable",
                        f"{pred.get('most_likely_home', 0)}-{pred.get('most_likely_away', 0)}"
                    )
                
                with col2:
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number+delta",
                        value=pred.get('prob_home', 33) * 100,
                        domain={'x': [0, 1], 'y': [0, 1]},
                        title={'text': "Local"},
                        gauge={
                            'axis': {'range': [None, 100]},
                            'bar': {'color': "#2ecc71"},
                            'steps': [
                                {'range': [0, 33], 'color': "#f0f2f6"},
                                {'range': [33, 66], 'color': "#e8f0fe"},
                            ]
                        }
                    ))
                    fig.update_layout(height=200, margin=dict(l=20, r=20, t=50, b=20))
                    st.plotly_chart(fig, use_container_width=True)
                
                with col3:
                    st.metric("Over 2.5", f"{pred.get('prob_over_25', 0):.1%}")
                    st.metric("BTTS", f"{pred.get('prob_btts', 0):.1%}")
                    
                    # Detectar Value Bet
                    if pred.get('value_bet'):
                        st.success(f"🎯 Value Bet: {pred['value_bet']}")
                        st.metric("Ventaja", f"{pred.get('value', 0):.1%}")
    else:
        st.info("ℹ️ No hay predicciones disponibles. Ejecuta el modelo primero.")

# --- TAB 3: ANÁLISIS HISTÓRICO ---
with tab3:
    st.subheader("📈 Análisis Histórico")
    
    if not df_hist.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Distribución de Goles")
            fig = go.Figure(go.Histogram(
                x=df_hist['total_goals'],
                nbinsx=15,
                marker_color='#3498db',
                name='Goles'
            ))
            fig.update_layout(
                height=350,
                xaxis_title="Total Goles",
                yaxis_title="Frecuencia",
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("📊 Heatmap de Resultados")
            # Crear matriz de resultados
            goal_matrix = df_hist.groupby(
                [df_hist['home_goals'].clip(upper=5), 
                 df_hist['away_goals'].clip(upper=5)]
            ).size().reset_index(name='count')
            
            pivot = goal_matrix.pivot(
                index='home_goals', 
                columns='away_goals', 
                values='count'
            ).fillna(0)
            
            fig = go.Figure(go.Heatmap(
                z=pivot.values,
                x=pivot.columns,
                y=pivot.index,
                colorscale='Viridis',
                text=pivot.values,
                texttemplate='%{text}',
                textfont={"size": 10},
                hoverongaps=False
            ))
            fig.update_layout(
                height=350,
                xaxis_title="Goles Visitante",
                yaxis_title="Goles Local"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Estadísticas adicionales
        st.subheader("📊 Estadísticas Clave")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Promedio Goles/Partido",
                f"{df_hist['total_goals'].mean():.2f}"
            )
        with col2:
            over_25 = (df_hist['total_goals'] > 2.5).mean()
            st.metric("% Over 2.5", f"{over_25:.1%}")
        with col3:
            btts = ((df_hist['home_goals'] > 0) & (df_hist['away_goals'] > 0)).mean()
            st.metric("% BTTS", f"{btts:.1%}")
        with col4:
            local_win = (df_hist['home_goals'] > df_hist['away_goals']).mean()
            st.metric("% Local Gana", f"{local_win:.1%}")
    else:
        st.info("ℹ️ No hay datos históricos disponibles")

# --- TAB 4: PARTIDOS HOY ---
with tab4:
    st.subheader("📋 Partidos de Hoy")
    
    if not df_today.empty:
        for _, match in df_today.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([2, 1, 2])
                with col1:
                    st.write(f"🏠 {match.get('home_name', 'Local')}")
                with col2:
                    st.write(f"*{match.get('home_goals', '-')} - {match.get('away_goals', '-')}*")
                with col3:
                    st.write(f"✈️ {match.get('away_name', 'Visita')}")
                st.markdown("---")
    else:
        st.info("ℹ️ No hay partidos programados para hoy")

# Footer
st.markdown("---")
st.caption("⚽ Football Predictor Pro v3.0 | Datos de Football-Data.org")
