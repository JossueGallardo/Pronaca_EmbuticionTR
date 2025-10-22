import pyodbc
import pandas as pd
import streamlit as st

def conectar_sql_server():
    """
    Conexión a SQL Server usando pyodbc 
    """
    connection_string = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=192.168.3.18\\SCMI_PRODUCCION;"
        "DATABASE=mms_planta;"
        "UID=genmmsdw;"
        "PWD=Pronaca2023;"
        "Connection Timeout=30;"
        "Login Timeout=30;"
        "TrustServerCertificate=yes;"
    )
    
    try:
        conn = pyodbc.connect(connection_string)
        return conn
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        return None

@st.cache_data(ttl=30)  # Cache por 30 segundos para tiempo real
def consultar_datos(query, force_refresh=False):
    """
    Función para ejecutar consultas SQL y retornar DataFrame
    """
    conn = conectar_sql_server()
    if conn:
        try:
            df = pd.read_sql(query, conn)
            conn.close()
            return df, None
        except Exception as e:
            conn.close()
            return None, f"Error en consulta: {e}"
    return None, "No se pudo conectar a la base de datos"

def consultar_datos_tiempo_real(query):
    """
    Función para consultas en tiempo real (sin caché)
    """
    conn = conectar_sql_server()
    if conn:
        try:
            df = pd.read_sql(query, conn)
            conn.close()
            return df, None
        except Exception as e:
            conn.close()
            return None, f"Error en consulta: {e}"
    return None, "No se pudo conectar a la base de datos"

def verificar_conexion():
    """
    Verificar si la conexión está funcionando
    """
    conn = conectar_sql_server()
    if conn:
        conn.close()
        return True
    return False

def obtener_tablas():
    """
    Obtener lista de tablas y vistas disponibles
    """
    query = """
    SELECT TABLE_NAME, TABLE_TYPE 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_TYPE IN ('BASE TABLE', 'VIEW')
    ORDER BY TABLE_TYPE, TABLE_NAME
    """
    df, error = consultar_datos(query)
    return df, error
