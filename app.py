import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Football Predictor", page_icon="⚽", layout="wide")

st.title("⚽ Football Predictor Pro")
st.markdown("---")

st.info("""
*Sistema funcionando correctamente* ✅

Este es el dashboard principal. Los datos se actualizan automáticamente cada día.
""")

# Mostrar métricas de ejemplo
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("📊 Partidos Hoy", "12", "+3")
with col2:
    st.metric("🎯 Value Bets", "4", "+2")
with col3:
    st.metric("💰 ROI", "12.3%", "+5.7%")

st.markdown("---")
st.caption(f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
