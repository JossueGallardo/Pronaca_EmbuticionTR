import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time
from database_connection import consultar_datos, consultar_datos_tiempo_real, verificar_conexion
from dashboard_peso_embuticion import dashboard_peso_embuticion

# Configuración de la página
st.set_page_config(
    page_title="Peso Embutición - Tiempo Real",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personalizado para el menú y ocultar elementos
st.markdown("""
<style>
    /* Ocultar header de Streamlit */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Ocultar sidebar completamente */
    .css-1d391kg {display: none;}
    section[data-testid="stSidebar"] {display: none;}
    
    /* Maximizar el contenido */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: none;
    }
    
    /* Estilo para pantalla completa */
    .main .block-container {
        max-width: 100%;
        padding: 0;
    }
    
    .main-header {
        background: linear-gradient(90deg, #1f77b4, #ff7f0e);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: white;
        text-align: center;
        margin: 0;
    }
    .dashboard-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        margin: 1rem 0;
        transition: transform 0.2s;
    }
    .dashboard-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .status-online {
        color: #28a745;
        font-weight: bold;
    }
    .status-offline {
        color: #dc3545;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Control principal de la aplicación
def main():
    """Función principal - ejecuta directamente el dashboard de tiempo real"""
    
    # Verificar conexión a la base de datos
    if not verificar_conexion():
        st.error("❌ Error: No se puede conectar a la base de datos")
        st.info("🔄 Reintentando conexión en 5 segundos...")
        time.sleep(5)
        st.rerun()
        return
    
    # Ejecutar directamente el dashboard de tiempo real
    from dashboard_peso_embuticion import dashboard_peso_embuticion_tiempo_real
    dashboard_peso_embuticion_tiempo_real()

if __name__ == "__main__":
    main()
