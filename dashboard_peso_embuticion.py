import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import sqlite3
import os
import math
import re
from database_connection import consultar_datos, verificar_conexion

# Funciones de SQLite removidas - volviendo al cálculo original

# --- Obtener las últimas N combinaciones (CODIGO, ODP) de las últimas 2 semanas ---
def obtener_ultimas_ordenes_embuticion(where_clause, cantidad=3):
    """Devuelve las últimas N combinaciones únicas de (CODIGO, ODP) con datos de embutición en las últimas 2 semanas."""
    try:
        query = f'''
        WITH DatosEmbuticion AS (
            SELECT FECHAINGRESO, PESONETO, NUMEMBALAJE, PROCESO, CODIGO, ODP
            FROM vwRegistrosDetallados
            WHERE {where_clause}
        ),
        KgEmbutidos AS (
            SELECT FECHAINGRESO, CODIGO, ODP,
                   SUM(CASE WHEN PROCESO = 'Embutición' THEN PESONETO ELSE 0 END) as _kgEmbutidos,
                   SUM(NUMEMBALAJE) as TotalEmbalajes
            FROM DatosEmbuticion
            GROUP BY FECHAINGRESO, CODIGO, ODP
        ),
        PesoSauciso AS (
            SELECT FECHAINGRESO, CODIGO, ODP, _kgEmbutidos, TotalEmbalajes,
                   CASE WHEN TotalEmbalajes > 0 THEN _kgEmbutidos / TotalEmbalajes ELSE 0 END as _PesoSauciso
            FROM KgEmbutidos
            WHERE _kgEmbutidos > 0
        ),
        UltimasOrdenes AS (
            SELECT CODIGO, ODP, MAX(FECHAINGRESO) as UltimaFecha
            FROM PesoSauciso
            WHERE CODIGO IS NOT NULL AND CODIGO != '' AND ODP IS NOT NULL AND ODP != ''
            GROUP BY CODIGO, ODP
        )
        SELECT TOP {cantidad} CODIGO, ODP
        FROM UltimasOrdenes
        ORDER BY UltimaFecha DESC
        '''
        df, _ = consultar_datos(query)
        if df is not None and not df.empty:
            return list(df.itertuples(index=False, name=None))  # [(CODIGO, ODP), ...]
        else:
            return []
    except Exception as e:
        st.error(f"Error al obtener últimas órdenes: {e}")
        return []
# --- DASHBOARD PESO EMBUTICION TIEMPO REAL (solo gráfico, sin filtros, lógica pantalla completa) ---
def dashboard_peso_embuticion_tiempo_real():
    """Vista tiempo real: solo el gráfico, alternancia de los últimos 3 códigos/órdenes de las últimas 2 semanas, sin filtros ni botón salir."""
    # Filtro fijo de las últimas 2 semanas
    where_clause = "FECHAINGRESO >= DATEADD(week, -2, GETDATE()) AND FECHAINGRESO IS NOT NULL AND CODIGO IS NOT NULL AND CODIGO != ''"
    # Alternancia y visualización por (CODIGO, ODP) únicos
    ultimas_ordenes = obtener_ultimas_ordenes_embuticion(where_clause, 3)
    if not ultimas_ordenes:
        st.warning("No hay órdenes recientes para mostrar.")
        return
    if 'indice_orden_actual_rt' not in st.session_state:
        st.session_state.indice_orden_actual_rt = 0
    if 'ultimo_cambio_orden_rt' not in st.session_state:
        st.session_state.ultimo_cambio_orden_rt = time.time()
    if 'lista_ordenes_anterior_rt' not in st.session_state:
        st.session_state.lista_ordenes_anterior_rt = []
    if ultimas_ordenes != st.session_state.lista_ordenes_anterior_rt:
        st.session_state.indice_orden_actual_rt = 0
        st.session_state.ultimo_cambio_orden_rt = time.time()
        st.session_state.lista_ordenes_anterior_rt = ultimas_ordenes.copy()
    tiempo_actual = time.time()
    tiempo_transcurrido = tiempo_actual - st.session_state.ultimo_cambio_orden_rt
    if tiempo_transcurrido >= 30 and len(ultimas_ordenes) > 1:
        st.session_state.indice_orden_actual_rt = (st.session_state.indice_orden_actual_rt + 1) % len(ultimas_ordenes)
        st.session_state.ultimo_cambio_orden_rt = tiempo_actual
    codigo_mostrado, odp_mostrado = ultimas_ordenes[st.session_state.indice_orden_actual_rt]
    # Layout igual que pantalla completa: columna lateral y gráfico
    col_info, col_grafico = st.columns([1, 7.5])
    with col_info:
        st.markdown("""
        <div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; position: sticky; top: 0;'>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div style='background-color: #ffffff; padding: 15px; border-radius: 8px; text-align: center; border-left: 5px solid #1f77b4; margin-top: 20px; width: 100%; overflow: hidden;'>
            <h1 style='color: #1f77b4; margin: 0; font-size: 2.3em; word-wrap: break-word; overflow-wrap: break-word; line-height: 1.2; max-width: 100%;'>
                {codigo_mostrado} <span style='font-size:0.6em; color:#888;'></span>
            </h1>
        </div>
        """, unsafe_allow_html=True)
        if len(ultimas_ordenes) > 1:
            tiempo_restante = max(0, 30 - int(tiempo_transcurrido))
            posicion_actual = st.session_state.indice_orden_actual_rt + 1
            total_ordenes = len(ultimas_ordenes)
            st.markdown(f"""
            <div style='background-color: #e8f4fd; padding: 15px; border-radius: 8px; text-align: center; margin-top: 15px;'>
                <p style='margin: 0; color: #1f77b4; font-size: 1.2em;'><b>Orden {posicion_actual} de {total_ordenes}</b></p>
                <p style='margin: 5px 0 0 0; color: #666; font-size: 1em;'>Siguiente en {tiempo_restante}s</p>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("<div style='margin-top: 20px;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color: #1f77b4; margin-bottom: 10px;'>Últimas órdenes:</h4>", unsafe_allow_html=True)
        for i, (codigo, odp) in enumerate(ultimas_ordenes):
            if (codigo, odp) == (codigo_mostrado, odp_mostrado):
                st.markdown(f"""
                <div style='background-color: #1f77b4; color: white; padding: 10px; border-radius: 5px; margin-bottom: 5px; text-align: center;'>
                    <b>{codigo}</b> ← Actual
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style='background-color: #ffffff; border: 2px solid #e0e0e0; padding: 10px; border-radius: 5px; margin-bottom: 5px; text-align: center;'>
                    {codigo}
                </div>
                """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col_grafico:
        if codigo_mostrado and odp_mostrado:
            query_orden = f"""
            WITH DatosEmbuticion AS (
                SELECT FECHAINGRESO, PESONETO, NUMEMBALAJE, PROCESO, CODIGO, ODP
                FROM vwRegistrosDetallados
                WHERE CODIGO = '{codigo_mostrado}'
                  AND ODP = '{odp_mostrado}'
                  AND FECHAINGRESO >= DATEADD(week, -2, GETDATE())
                  AND FECHAINGRESO IS NOT NULL
            ),
            KgEmbutidos AS (
                SELECT FECHAINGRESO, CODIGO,
                       SUM(CASE WHEN PROCESO = 'Embutición' THEN PESONETO ELSE 0 END) as _kgEmbutidos,
                       SUM(NUMEMBALAJE) as TotalEmbalajes
                FROM DatosEmbuticion
                GROUP BY FECHAINGRESO, CODIGO
            ),
            PesoSauciso AS (
                SELECT FECHAINGRESO, CODIGO, _kgEmbutidos, TotalEmbalajes,
                       CASE WHEN TotalEmbalajes > 0 THEN _kgEmbutidos / TotalEmbalajes ELSE 0 END as _PesoSauciso
                FROM KgEmbutidos
                WHERE _kgEmbutidos > 0
            )
            SELECT TOP 8 FECHAINGRESO, CODIGO, _kgEmbutidos, TotalEmbalajes, _PesoSauciso
            FROM PesoSauciso
            WHERE FECHAINGRESO >= DATEADD(week, -2, GETDATE())
            ORDER BY FECHAINGRESO DESC
            """
            df_orden, _ = consultar_datos(query_orden)
            if df_orden is not None and not df_orden.empty:
                df_orden = df_orden.sort_values('FECHAINGRESO')
                # Usar cálculo original de peso sauciso
                crear_grafico_pantalla_completa_con_orden(df_orden, codigo_mostrado, odp_mostrado, "FECHAINGRESO >= DATEADD(week, -2, GETDATE())")
            else:
                st.warning(f"No se encontraron datos para la orden {codigo_mostrado} | ODP: {odp_mostrado}")
        else:
            st.warning("No hay datos disponibles para mostrar en tiempo real")
    # Auto-actualización cada 1 segundo
    time.sleep(1)
    st.rerun()

def _convertir_filtros_a_fecha_creacion(where_clause):
    """
    Convertir filtros de FECHAINGRESO a filtros de FechaCreacion
    Ejemplo: YEAR(FECHAINGRESO) = 2025 -> YEAR(FechaCreacion) = 2025
    Maneja correctamente el caso día "Todas" + semana específica
    """
    import re
    
    filtros_fecha_creacion = []
    
    # Extraer año
    if "YEAR(FECHAINGRESO)" in where_clause:
        year_match = re.search(r"YEAR\(FECHAINGRESO\) = (\d+)", where_clause)
        if year_match:
            year = year_match.group(1)
            filtros_fecha_creacion.append(f"YEAR(FechaCreacion) = {year}")
    
    # Extraer semana  
    if "DATEPART(week, FECHAINGRESO)" in where_clause:
        week_match = re.search(r"DATEPART\(week, FECHAINGRESO\) = (\d+)", where_clause)
        if week_match:
            week = week_match.group(1)
            filtros_fecha_creacion.append(f"DATEPART(week, FechaCreacion) = {week}")
    
    # Extraer dia de la semana 
    if "DATENAME(weekday, FECHAINGRESO)" in where_clause:
        day_match = re.search(r"DATENAME\(weekday, FECHAINGRESO\) = '(\w+)'", where_clause)
        if day_match:
            day_en = day_match.group(1)  # Día en ingles del filtro
            # Mapear dias
            day_mapping = {
                'Monday': 'lunes',
                'Tuesday': 'martes', 
                'Wednesday': 'miércoles',
                'Thursday': 'jueves',
                'Friday': 'viernes',
                'Saturday': 'sábado',
                'Sunday': 'domingo',
                'lunes': 'Monday',
                'martes': 'Tuesday',
                'miércoles': 'Wednesday', 
                'jueves': 'Thursday',
                'viernes': 'Friday',
                'sábado': 'Saturday',
                'domingo': 'Sunday'
            }
            
            # Probar ambos formatos para compatibilidad
            filtros_fecha_creacion.append(f"(DATENAME(weekday, FechaCreacion) = '{day_en}' OR DATENAME(weekday, FechaCreacion) = '{day_mapping.get(day_en, day_en)}')")
    
    return " AND " + " AND ".join(filtros_fecha_creacion) if filtros_fecha_creacion else ""

def obtener_codigo_orden_por_producto(codigo_producto, where_clause):
    """
    Obtener el CodigoOrden correspondiente a un CodigoProducto 
    basado en los filtros aplicados para mostrar progreso específico por orden
    Prioriza ordnes que tienen registros de embuticion activos
    """
    try:
        # Convertir filtros para buscar en FechaCreacion
        filtros_fecha_creacion = _convertir_filtros_a_fecha_creacion(where_clause)
        
        # Buscar ordenes que tengan registros de embuticion primero
        query = f"""
        WITH OrdenesConEmbuticion AS (
            -- Buscar ordenes que SÍ tienen registros de embutición en el período filtrado
            SELECT DISTINCT 
                od.CodigoOrden,
                od.CodigoProducto,
                od.FechaCreacion,
                1 as TieneEmbuticion
            FROM vwOrdenDocumento od
            INNER JOIN vwRegistrosDetallados rd ON od.CodigoOrden = rd.ODP
            WHERE od.CodigoProducto = '{codigo_producto}'
                {filtros_fecha_creacion}
                AND rd.CODIGO = '{codigo_producto}'
                AND rd.PROCESO = 'Embutición'
                AND {where_clause}
        ),
        OrdenesDelProducto AS (
            -- Buscar TODAS las ordenes del producto en el periodo 
            SELECT DISTINCT
                od.CodigoOrden,
                od.CodigoProducto,
                od.FechaCreacion,
                0 as TieneEmbuticion
            FROM vwOrdenDocumento od
            WHERE od.CodigoProducto = '{codigo_producto}'
                {filtros_fecha_creacion}
        ),
        OrdenesCompletas AS (
            -- Combinar ambas consultas, priorizando las que tienen embuticion
            SELECT CodigoOrden, CodigoProducto, FechaCreacion, TieneEmbuticion
            FROM OrdenesConEmbuticion
            UNION
            SELECT CodigoOrden, CodigoProducto, FechaCreacion, TieneEmbuticion 
            FROM OrdenesDelProducto
            WHERE CodigoOrden NOT IN (SELECT CodigoOrden FROM OrdenesConEmbuticion)
        )
        SELECT TOP 1 
            CodigoOrden,
            CodigoProducto,
            FechaCreacion,
            TieneEmbuticion
        FROM OrdenesCompletas
        ORDER BY 
            TieneEmbuticion DESC,  -- Priorizar ordenes con embuticion
            FechaCreacion DESC     -- Luego por fecha mas reciente
        """
        
        df_orden, _ = consultar_datos(query)
        
        if df_orden is not None and not df_orden.empty:
            return df_orden.iloc[0]['CodigoOrden']
        else:
            return None
            
    except Exception as e:
        st.error(f"Error obteniendo CodigoOrden: {e}")
        return None

def calcular_progreso_embuticion_bi(codigo_producto, where_clause, codigo_orden=None):
    """
    Calcular progreso de embuticion
    
    Logica:
    - MasaInicial = vwOrdenDocumento[PesoODP]*1+(vwOrdenDocumento[PesoODP]*(RELATED(vwProductoFormula[PorcentajeMermaMP])/100))
    - Embutido = sum(vwRegistrosDetallados[PESONETO]) WHERE PROCESO='Embutición'
    - Porcentaje = (sum(Embutido))/(sum(MasaInicial))
    
    CASOS ESPECIALES:
    - Manejar embutidos en dias diferentes a creación de orden
    - Filtros semana + dia "Todos" 
    - Calcular progreso por CodigoOrden específico si se proporciona
    """
    try:
        # Convertir filtros de FECHAINGRESO a FechaCreacion
        filtros_fecha_creacion = _convertir_filtros_a_fecha_creacion(where_clause)
        
        # Construir query 
        if codigo_orden:
            # Calcular progreso para una orden especifica
            query = f"""
            WITH 
            -- 1. Obtener ORDEN ESPECIFICA con merma de MASA unicamente
            OrdenEspecifica AS (
                SELECT DISTINCT
                    od.CodigoProducto,
                    od.CodigoOrden,
                    od.PesoODP,
                    od.FechaCreacion,
                    -- Relacionar con la merma de MASA 
                    ISNULL(pf.PorcentajeMermaMP, 0) as PorcentajeMermaMP,
                    pf.CodigoMp
                FROM vwOrdenDocumento od
                LEFT JOIN vwProductoFormula pf ON od.CodigoProducto = pf.CodigoProducto
                WHERE od.CodigoProducto = '{codigo_producto}'
                    AND od.CodigoOrden = '{codigo_orden}'
                    AND pf.CodigoMp LIKE 'YY06%'  -- Solo merma de masa (empieza con YY06)
                    AND ISNULL(pf.PorcentajeMermaMP, 0) > 0  -- Solo ordenes con merma aplicada
            ),
            
            -- 2. Calcular MasaInicial de la orden especifica
            MasaInicialOrden AS (
                SELECT 
                    CodigoOrden,
                    CodigoProducto,
                    -- Calcular MasaInicial 
                    -- MasaInicial = PesoODP*1+(PesoODP*(PorcentajeMermaMP/100))
                    SUM(PesoODP * 1 + (PesoODP * (PorcentajeMermaMP / 100.0))) as TotalKgDebenEmbutir
                FROM OrdenEspecifica
                GROUP BY CodigoOrden, CodigoProducto
            ),
            
            -- 3. Calcular Embutido de la orden especifica
            -- FILTRAR POR ODP = CodigoOrden PARA OBTENER SOLO LOS KG DE ESTA ORDEN ESPECÍFICA
            EmbutidoOrden AS (
                SELECT 
                    SUM(CASE WHEN PROCESO = 'Embutición' THEN PESONETO ELSE 0 END) as TotalKgEmbutidos
                FROM vwRegistrosDetallados 
                WHERE CODIGO = '{codigo_producto}' 
                    AND ODP = '{codigo_orden}'  -- CLAVE: Filtrar por la orden especifica
                    AND PROCESO = 'Embutición'
                    AND {where_clause}
            )

            -- 4. Resultado final para la orden especifica
            SELECT 
                ISNULL(mio.TotalKgDebenEmbutir, 0) as KgDebenEmbutir,
                ISNULL(eo.TotalKgEmbutidos, 0) as KgEmbutidos,
                mio.CodigoOrden,
                -- Porcentaje = (sum(Embutido))/(sum(MasaInicial))
                CASE 
                    WHEN ISNULL(mio.TotalKgDebenEmbutir, 0) > 0 
                    THEN (ISNULL(eo.TotalKgEmbutidos, 0) / mio.TotalKgDebenEmbutir) * 100
                    ELSE 0 
                END as PorcentajeProgreso
            FROM MasaInicialOrden mio
            CROSS JOIN EmbutidoOrden eo
            """
        else:
            # Query original para producto completo
            query = f"""
            WITH 
            -- 1. Obtener ordenes con merma de MASA unicamente (CodigoMp que empiece con 'YY06')
            OrdenesConFechas AS (
                SELECT DISTINCT
                    od.CodigoProducto,
                    od.PesoODP,
                    od.FechaCreacion,
                    -- Relacionar con la merma de Masa
                    ISNULL(pf.PorcentajeMermaMP, 0) as PorcentajeMermaMP,
                    pf.CodigoMp
                FROM vwOrdenDocumento od
                LEFT JOIN vwProductoFormula pf ON od.CodigoProducto = pf.CodigoProducto
                WHERE od.CodigoProducto = '{codigo_producto}'
                    AND pf.CodigoMp LIKE 'YY06%'  -- Solo merma de masa (empieza con YY06)
                    AND ISNULL(pf.PorcentajeMermaMP, 0) > 0  -- Solo ordenes con merma aplicada
            ),

            -- 2. Filtrar ordenes por las fechas que corresponden a los filtros aplicados
            -- Usa filtros convertidos a FechaCreacion para ordenes
            OrdenesDelPeriodo AS (
                SELECT 
                    CodigoProducto,
                    PesoODP,
                    PorcentajeMermaMP,
                    FechaCreacion,
                    CodigoMp,
                    -- Calcular MasaInicial 
                    -- MasaInicial = PesoODP*1+(PesoODP*(PorcentajeMermaMP/100))
                    PesoODP * 1 + (PesoODP * (PorcentajeMermaMP / 100.0)) as MasaInicial
                FROM OrdenesConFechas
                WHERE 1=1
                    {filtros_fecha_creacion}
            ),
            
            -- 3. Calcular total de MasaInicial (kg que se deben embutir)
            TotalMasaInicial AS (
                SELECT 
                    SUM(MasaInicial) as TotalKgDebenEmbutir
                FROM OrdenesDelPeriodo
            ),
            
            -- 4. Calcular Embutido del período (kg que van embutidos)
            -- Filtrar SOLO embutidos con filtros temporales precisos
            TotalEmbutido AS (
                SELECT 
                    SUM(CASE WHEN PROCESO = 'Embutición' THEN PESONETO ELSE 0 END) as TotalKgEmbutidos
                FROM vwRegistrosDetallados 
                WHERE CODIGO = '{codigo_producto}' 
                    AND PROCESO = 'Embutición'
                    AND {where_clause}
            )
            
            -- 5. Resultado final con la logica 
            SELECT 
                ISNULL(tmi.TotalKgDebenEmbutir, 0) as KgDebenEmbutir,
                ISNULL(te.TotalKgEmbutidos, 0) as KgEmbutidos,
                NULL as CodigoOrden,
                -- Porcentaje = (sum(Embutido))/(sum(MasaInicial))
                CASE 
                    WHEN ISNULL(tmi.TotalKgDebenEmbutir, 0) > 0 
                    THEN (ISNULL(te.TotalKgEmbutidos, 0) / tmi.TotalKgDebenEmbutir) * 100
                    ELSE 0 
                END as PorcentajeProgreso
            FROM TotalMasaInicial tmi
            CROSS JOIN TotalEmbutido te
            """
        
        df_progreso, _ = consultar_datos(query)
        
        if df_progreso is not None and not df_progreso.empty:
            kg_deben_embutir = df_progreso.iloc[0]['KgDebenEmbutir']
            kg_embutidos = df_progreso.iloc[0]['KgEmbutidos']
            porcentaje = df_progreso.iloc[0]['PorcentajeProgreso']

            # Calcular saucissos faltantes para orden especifica
            saucissos_faltantes = 0
            if codigo_orden:
                # Consulta para obtener todos los _PesoSauciso de la orden especifica
                query_saucissos = f"""
                WITH DatosEmbuticion AS (
                    SELECT 
                        FECHAINGRESO,
                        PESONETO,
                        NUMEMBALAJE,
                        PROCESO,
                        CODIGO,
                        ODP
                    FROM vwRegistrosDetallados 
                    WHERE CODIGO = '{codigo_producto}' 
                        AND ODP = '{codigo_orden}'
                        AND PROCESO = 'Embutición'
                        AND {where_clause}
                ),
                KgEmbutidos AS (
                    SELECT 
                        FECHAINGRESO,
                        SUM(CASE WHEN PROCESO = 'Embutición' THEN PESONETO ELSE 0 END) as _kgEmbutidos,
                        SUM(NUMEMBALAJE) as TotalEmbalajes
                    FROM DatosEmbuticion
                    GROUP BY FECHAINGRESO
                ),
                PesoSauciso AS (
                    SELECT 
                        FECHAINGRESO,
                        _kgEmbutidos,
                        TotalEmbalajes,
                        CASE 
                            WHEN TotalEmbalajes > 0 THEN _kgEmbutidos / TotalEmbalajes 
                            ELSE 0 
                        END as _PesoSauciso
                    FROM KgEmbutidos
                    WHERE _kgEmbutidos > 0
                )
                SELECT 
                    AVG(_PesoSauciso) as PromedioSaucisso,
                    COUNT(*) as TotalSaucissos
                FROM PesoSauciso
                WHERE _PesoSauciso > 0
                """
                
                try:
                    df_saucissos, _ = consultar_datos(query_saucissos)
                    if df_saucissos is not None and not df_saucissos.empty and df_saucissos.iloc[0]['PromedioSaucisso'] is not None:
                        promedio_saucisso = df_saucissos.iloc[0]['PromedioSaucisso']
                        kg_faltantes = kg_deben_embutir - kg_embutidos
                        
                        if promedio_saucisso > 0 and kg_faltantes > 0:
                            import math
                            saucissos_faltantes = math.ceil(kg_faltantes / promedio_saucisso)
                        else:
                            saucissos_faltantes = 0
                except Exception as e:
                    saucissos_faltantes = 0
            
            # Incluir CodigoOrden si esta disponible
            resultado = {
                'kg_deben_embutir': kg_deben_embutir,
                'kg_embutidos': kg_embutidos,
                'porcentaje': porcentaje,
                'saucissos_faltantes': saucissos_faltantes
            }
            
            # Agregar CodigoOrden si está presente en el resultado
            if 'CodigoOrden' in df_progreso.columns and df_progreso.iloc[0]['CodigoOrden'] is not None:
                resultado['codigo_orden'] = df_progreso.iloc[0]['CodigoOrden']
            
            return resultado
        else:
            return {'kg_deben_embutir': 0, 'kg_embutidos': 0, 'porcentaje': 0, 'saucissos_faltantes': 0}
            
    except Exception as e:
        st.error(f"Error calculando progreso BI: {e}")
        return {'kg_deben_embutir': 0, 'kg_embutidos': 0, 'porcentaje': 0, 'saucissos_faltantes': 0}

def mostrar_vista_normal(df_peso_sauciso):
    """Vista normal del gráfico"""
    # Calcular promedio para linea de referencia
    promedio = df_peso_sauciso['_PesoSauciso'].mean()
    
    # Grafico de Linea
    fig = go.Figure()
    
    # Linea de referencia (promedio) - línea rosa/roja punteada
    fig.add_hline(
        y=promedio, 
        line_dash="dash", 
        line_color="rgba(255, 105, 180, 0.8)",
        line_width=2
    )
    
    # Linea principal verde
    fig.add_trace(go.Scatter(
        x=df_peso_sauciso['FECHAINGRESO'],
        y=df_peso_sauciso['_PesoSauciso'],
        mode='lines+markers+text',
        line=dict(color='green', width=2),
        marker=dict(size=6, color='green'),
        text=[f"{val:.2f}" for val in df_peso_sauciso['_PesoSauciso']], #Decimales en grafico
        textposition="top center",
        textfont=dict(size=10, color='black'),
        showlegend=False,
        hovertemplate='<b>Fecha:</b> %{x}<br>' +
                     '<b>Peso sauciso:</b> %{y:.2f}<br>' +
                     '<extra></extra>'
    ))
    
    # Configurar layout con grafico más grande y barra de desplazamiento
    fig.update_layout(
        title=dict(
            text='Peso sauciso',
            font=dict(size=18, color='black'),
            x=0,
            xanchor='left'
        ),
        height=700,  # Alto para mejor visualización
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=80, r=80, t=100, b=150),
        xaxis=dict(
            showgrid=True,
            gridcolor='lightgray',
            gridwidth=1,
            tickangle=90,
            tickfont=dict(size=12),
            showline=True,
            linecolor='black',
            tickformat='%d/%m/%Y<br>%H:%M',
            # Configurar rango de navegacin horizontal
            rangeslider=dict(
                visible=True,
                thickness=0.1,
                bgcolor='rgba(0,0,0,0.1)',
                bordercolor='gray',
                borderwidth=1
            ),
            # Mostrar solo una ventana de tiempo al inicio
            range=[
                df_peso_sauciso['FECHAINGRESO'].iloc[max(0, len(df_peso_sauciso)-20)],
                df_peso_sauciso['FECHAINGRESO'].iloc[-1]
            ] if len(df_peso_sauciso) > 20 else [
                df_peso_sauciso['FECHAINGRESO'].min(),
                df_peso_sauciso['FECHAINGRESO'].max()
            ]
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='lightgray',
            gridwidth=1,
            tickfont=dict(size=12),
            showline=True,
            linecolor='black',
            # Rango automático
            range=[0, df_peso_sauciso['_PesoSauciso'].max() * 1.2]
        ),
        # Configuracion para mejor interactividad
        dragmode='pan',
        showlegend=False
    )
    
    # Mostrar el grafico con configuración mejorada
    st.plotly_chart(fig, use_container_width=True, config={
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToShow': ['pan2d', 'zoom2d', 'zoomin2d', 'zoomout2d', 'autoScale2d', 'resetScale2d'],
        'scrollZoom': True
    })
    
    # Mostrar DataFrame con datos detallados debajo del gráfico
    st.subheader("📋 Datos Detallados")
    
    # Preparar el DataFrame para mostrar
    df_mostrar = df_peso_sauciso.copy()
    
    # Formatear las columnas para mejor visualización
    if not df_mostrar.empty:
        # Agregar columnas de fecha y hora separadas
        df_mostrar['Fecha'] = df_mostrar['FECHAINGRESO'].dt.strftime('%d/%m/%Y')
        df_mostrar['Hora'] = df_mostrar['FECHAINGRESO'].dt.strftime('%H:%M:%S')
        
        # Seleccionar las columnas que queremos mostrar (verificando que existan)
        columnas_mostrar = []
        
        # Columnas básicas obligatorias
        if 'CODIGO' in df_mostrar.columns:
            columnas_mostrar.append('CODIGO')
        
        # ODP puede no existir en algunos casos
        if 'ODP' in df_mostrar.columns:
            columnas_mostrar.append('ODP')
        
        # Fecha y hora (siempre deben existir)
        columnas_mostrar.extend(['Fecha', 'Hora'])
        
        # Peso sauciso (obligatorio)
        if '_PesoSauciso' in df_mostrar.columns:
            columnas_mostrar.append('_PesoSauciso')
        
        # Crear DataFrame final para mostrar
        df_final = df_mostrar[columnas_mostrar].copy()
        
        # Renombrar columnas para mejor presentación
        nombres_columnas = []
        for col in columnas_mostrar:
            if col == 'CODIGO':
                nombres_columnas.append('Código')
            elif col == 'ODP':
                nombres_columnas.append('ODP')
            elif col == 'Fecha':
                nombres_columnas.append('Fecha')
            elif col == 'Hora':
                nombres_columnas.append('Hora')
            elif col == '_PesoSauciso':
                nombres_columnas.append('Peso Sauciso (kg)')
            else:
                nombres_columnas.append(col)
        
        df_final.columns = nombres_columnas
        
        # Formatear números con 2 decimales (solo columnas numéricas)
        for col in df_final.columns:
            if 'Peso' in col:
                # Verificar que la columna sea numérica antes de redondear
                if pd.api.types.is_numeric_dtype(df_final[col]):
                    df_final[col] = df_final[col].round(2)
                else:
                    # Intentar convertir a numérico si es posible
                    try:
                        df_final[col] = pd.to_numeric(df_final[col], errors='coerce').round(2)
                    except:
                        # Si no se puede convertir, mantener el valor original
                        pass
        
        # Mostrar el DataFrame
        # Crear configuración de columnas dinámicamente
        column_config = {}
        
        for col in df_final.columns:
            if col == "Código":
                column_config[col] = st.column_config.TextColumn("Código", width="small")
            elif col == "ODP":
                column_config[col] = st.column_config.TextColumn("ODP", width="medium")
            elif col == "Fecha":
                column_config[col] = st.column_config.TextColumn("Fecha", width="small")
            elif col == "Hora":
                column_config[col] = st.column_config.TextColumn("Hora", width="small")
            elif col == "Peso Sauciso (kg)":
                column_config[col] = st.column_config.NumberColumn(
                    "Peso Sauciso (kg)",
                    width="medium",
                    format="%.2f"
                )
        
        st.dataframe(
            df_final,
            use_container_width=True,
            hide_index=True,
            column_config=column_config
        )
        
        # Mostrar estadísticas resumidas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Registros", len(df_final))
        with col2:
            st.metric("Peso Promedio", f"{df_final['Peso Sauciso (kg)'].mean():.2f} kg")
        with col3:
            st.metric("Peso Mínimo", f"{df_final['Peso Sauciso (kg)'].min():.2f} kg")
        with col4:
            st.metric("Peso Máximo", f"{df_final['Peso Sauciso (kg)'].max():.2f} kg")
    else:
        st.info("No hay datos disponibles para mostrar en la tabla.")

def obtener_ultimos_codigos_con_orden(where_clause, cantidad=3):
    """Obtener las últimas N combinaciones únicas de (CODIGO, ODP) que tengan datos de embutición"""
    try:
        query = f"""
        WITH DatosEmbuticion AS (
            SELECT 
                FECHAINGRESO,
                PESONETO,
                NUMEMBALAJE,
                PROCESO,
                CODIGO,
                ODP
            FROM vwRegistrosDetallados 
            WHERE {where_clause}
        ),
        KgEmbutidos AS (
            SELECT 
                FECHAINGRESO,
                CODIGO,
                ODP,
                SUM(CASE WHEN PROCESO = 'Embutición' THEN PESONETO ELSE 0 END) as _kgEmbutidos,
                SUM(NUMEMBALAJE) as TotalEmbalajes
            FROM DatosEmbuticion
            GROUP BY FECHAINGRESO, CODIGO, ODP
        ),
        PesoSauciso AS (
            SELECT 
                FECHAINGRESO,
                CODIGO,
                ODP,
                _kgEmbutidos,
                TotalEmbalajes,
                CASE 
                    WHEN TotalEmbalajes > 0 THEN _kgEmbutidos / TotalEmbalajes 
                    ELSE 0 
                END as _PesoSauciso
            FROM KgEmbutidos
            WHERE _kgEmbutidos > 0
        ),
        UltimosPorCodigoOrden AS (
            SELECT 
                CODIGO,
                ODP,
                MAX(FECHAINGRESO) as UltimaFecha
            FROM PesoSauciso
            WHERE CODIGO IS NOT NULL 
                AND CODIGO != ''
                AND ODP IS NOT NULL
                AND ODP != ''
            GROUP BY CODIGO, ODP
        )
        SELECT TOP {cantidad} CODIGO, ODP
        FROM UltimosPorCodigoOrden
        ORDER BY UltimaFecha DESC
        """
        
        df_codigos, _ = consultar_datos(query)
        
        if df_codigos is not None and not df_codigos.empty:
            return list(df_codigos.itertuples(index=False, name=None))  # [(CODIGO, ODP), ...]
        else:
            return []
    except Exception as e:
        st.error(f"Error al obtener últimos códigos con orden: {e}")
        return []

def mostrar_vista_pantalla_completa(df_peso_sauciso, ultimo_codigo, where_clause):
    """Vista de pantalla completa con alternancia de últimas 3 combinaciones CODIGO+ODP"""
    
    # Limpiar la interfaz para pantalla completa
    st.empty()
    
    # Obtener las ultimas 3 combinaciones únicas CODIGO+ODP
    ultimas_combinaciones = obtener_ultimos_codigos_con_orden(where_clause, 3)
    
    # Inicializar session state para alternancia
    if 'indice_combinacion_actual' not in st.session_state:
        st.session_state.indice_combinacion_actual = 0
    if 'ultimo_cambio_combinacion' not in st.session_state:
        st.session_state.ultimo_cambio_combinacion = time.time()
    if 'lista_combinaciones_anterior' not in st.session_state:
        st.session_state.lista_combinaciones_anterior = []
    
    # Si no hay combinaciones, usar el ultimo codigo conocido con ODP vacío
    if not ultimas_combinaciones:
        ultimas_combinaciones = [(ultimo_codigo, "N/A")] if ultimo_codigo != "Sin datos" else [("Sin datos", "N/A")]
    
    # Si cambió la lista de combinaciones, reiniciar alternancia
    if ultimas_combinaciones != st.session_state.lista_combinaciones_anterior:
        st.session_state.indice_combinacion_actual = 0
        st.session_state.ultimo_cambio_combinacion = time.time()
        st.session_state.lista_combinaciones_anterior = ultimas_combinaciones.copy()
    
    # Alternar combinaciones cada 30 segundos
    tiempo_actual = time.time()
    tiempo_transcurrido = tiempo_actual - st.session_state.ultimo_cambio_combinacion
    
    if tiempo_transcurrido >= 30 and len(ultimas_combinaciones) > 1:
        st.session_state.indice_combinacion_actual = (st.session_state.indice_combinacion_actual + 1) % len(ultimas_combinaciones)
        st.session_state.ultimo_cambio_combinacion = tiempo_actual
    
    # Combinación que se está mostrando actualmente
    if ultimas_combinaciones:
        codigo_mostrado, odp_mostrado = ultimas_combinaciones[st.session_state.indice_combinacion_actual]
    else:
        codigo_mostrado, odp_mostrado = ultimo_codigo, "N/A"
    
    # Crear layout de pantalla completa con más espacio para el grafico
    col_info, col_grafico = st.columns([1, 7.5])  # Más espacio para el grafico (reducir sección izquierda)
    
    with col_info:
        # Franja lateral izquierda con codigo actual y lista de combinaciones
        st.markdown("""
        <div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; position: sticky; top: 0;'>
        """, unsafe_allow_html=True)
        
        # Codigo actualmente mostrado con ODP
        st.markdown(f"""
        <div style='background-color: #ffffff; padding: 15px; border-radius: 8px; text-align: center; border-left: 5px solid #1f77b4; margin-top: 20px; width: 100%; overflow: hidden;'>
            <h1 style='color: #1f77b4; margin: 0; font-size: 2.3em; word-wrap: break-word; overflow-wrap: break-word; line-height: 1.2; max-width: 100%;'>
                {codigo_mostrado} <span style='font-size:0.5em; color:#888;'><br>ODP: {odp_mostrado}</span>
            </h1>
        </div>
        """, unsafe_allow_html=True)

        # Mostrar información de alternancia solo si hay más de una combinación
        if len(ultimas_combinaciones) > 1:
            tiempo_restante = max(0, 30 - int(tiempo_transcurrido))
            posicion_actual = st.session_state.indice_combinacion_actual + 1
            total_combinaciones = len(ultimas_combinaciones)
            
            st.markdown(f"""
            <div style='background-color: #e8f4fd; padding: 15px; border-radius: 8px; text-align: center; margin-top: 15px;'>
                <p style='margin: 0; color: #1f77b4; font-size: 1.2em;'><b>Orden {posicion_actual} de {total_combinaciones}</b></p>
                <p style='margin: 5px 0 0 0; color: #666; font-size: 1em;'>Siguiente en {tiempo_restante}s</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Lista de todas las combinaciones
        st.markdown("<div style='margin-top: 20px;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color: #1f77b4; margin-bottom: 10px;'>Últimas órdenes:</h4>", unsafe_allow_html=True)
        
        for i, (codigo, odp) in enumerate(ultimas_combinaciones):
            if (codigo, odp) == (codigo_mostrado, odp_mostrado):
                # Combinación actual resaltada
                st.markdown(f"""
                <div style='background-color: #1f77b4; color: white; padding: 10px; border-radius: 5px; margin-bottom: 5px; text-align: center;'>
                    <b>{codigo}</b><br><small>ODP: {odp}</small><br>← Actual
                </div>
                """, unsafe_allow_html=True)
            else:
                # Otras combinaciones
                st.markdown(f"""
                <div style='background-color: #ffffff; border: 2px solid #e0e0e0; padding: 10px; border-radius: 5px; margin-bottom: 5px; text-align: center;'>
                    <b>{codigo}</b><br><small>ODP: {odp}</small>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Boton para salir de pantalla completa
        if st.button("↩️ Salir", key="salir_pc", use_container_width=True):
            st.session_state['modo_pantalla_completa'] = False
            st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col_grafico:
        # Filtrar datos para mostrar la combinación actualmente seleccionada
        if codigo_mostrado != "Sin datos" and codigo_mostrado and odp_mostrado != "N/A":
            # Consulta para obtener SOLO LOS ULTIMOS DATOS de la combinación mostrada
            query_combinacion_especifica = f"""
            WITH DatosEmbuticion AS (
                SELECT 
                    FECHAINGRESO,
                    PESONETO,
                    NUMEMBALAJE,
                    PROCESO,
                    CODIGO,
                    ODP
                FROM vwRegistrosDetallados 
                WHERE CODIGO = '{codigo_mostrado}' 
                    AND ODP = '{odp_mostrado}'
                    AND {where_clause}
            ),
            KgEmbutidos AS (
                SELECT 
                    FECHAINGRESO,
                    CODIGO,
                    SUM(CASE WHEN PROCESO = 'Embutición' THEN PESONETO ELSE 0 END) as _kgEmbutidos,
                    SUM(NUMEMBALAJE) as TotalEmbalajes
                FROM DatosEmbuticion
                GROUP BY FECHAINGRESO, CODIGO
            ),
            PesoSauciso AS (
                SELECT 
                    FECHAINGRESO,
                    CODIGO,
                    _kgEmbutidos,
                    TotalEmbalajes,
                    CASE 
                        WHEN TotalEmbalajes > 0 THEN _kgEmbutidos / TotalEmbalajes 
                        ELSE 0 
                    END as _PesoSauciso
                FROM KgEmbutidos
                WHERE _kgEmbutidos > 0
            )
            SELECT TOP 8 
                FECHAINGRESO,
                CODIGO,
                _kgEmbutidos,
                TotalEmbalajes,
                _PesoSauciso
            FROM PesoSauciso
            ORDER BY FECHAINGRESO DESC
            """
            
            df_combinacion, _ = consultar_datos(query_combinacion_especifica)
            
            if df_combinacion is not None and not df_combinacion.empty:
                # Ordenar por fecha ascendente para mostrar cronologicamente el grafico
                df_combinacion = df_combinacion.sort_values('FECHAINGRESO')
                # Usar cálculo original de peso sauciso
                # Crear gráfico específico para la combinación CODIGO+ODP
                crear_grafico_pantalla_completa_con_orden(df_combinacion, codigo_mostrado, odp_mostrado, where_clause)
            else:
                st.warning(f"No se encontraron datos para {codigo_mostrado} | ODP: {odp_mostrado}")
        else:
            st.warning("No hay datos disponibles para mostrar en pantalla completa")

    # Auto-actualizacion específica para pantalla completa cada 1 segundo
    time.sleep(1)
    st.rerun()

def crear_grafico_pantalla_completa_con_orden(df_peso_sauciso, codigo_actual, odp_actual, where_clause):
    """Crear grafico optimizado para pantalla completa y TV con barra de progreso para combinación CODIGO+ODP específica"""
    
    # Evitar renderizado múltiple con un placeholder único
    container = st.container()
    
    with container:
        # Calcular progreso usando la logica con orden específica
        progreso = calcular_progreso_embuticion_bi(codigo_actual, where_clause, odp_actual)
        
        # Configurar el grafico de lineas
        fig = go.Figure()
        
        # Agregar linea principal optimizada para TV
        fig.add_trace(go.Scatter(
            x=df_peso_sauciso['FECHAINGRESO'],
            y=df_peso_sauciso['_PesoSauciso'],
            mode='lines+markers+text',
            name=f'Código {codigo_actual} - ODP {odp_actual}',
            line=dict(color='#1f77b4', width=6),  # Linea mas gruesa para TV
            marker=dict(size=12, symbol='circle', color='#1f77b4'),
            text=[f"{val:.2f}" for val in df_peso_sauciso['_PesoSauciso']], # Decimales en grafico
            textposition="top center",
            textfont=dict(size=20, color='#1f77b4'),  # Texto mas grande para TV 
            hovertemplate='<b>Fecha:</b> %{x}<br><b>Peso Sauciso:</b> %{y:.2f} kg<extra></extra>'
        ))
        
        # Configuracion del layout optimizado para pantalla completa
        fig.update_layout(
            title=dict(
                text=f'<b>Orden: {odp_actual} | <span style="color: {"red" if progreso["saucissos_faltantes"] < 34 else "#000000"}">Sau.Fal: {progreso["saucissos_faltantes"]}</span></b>',
                font=dict(size=28, color="#000000"),  # Titulo mas grande 
                x=0.100
            ),
            annotations=[
                # Titulo de la barra de progreso 
                dict(
                    text=f"<b>Progreso: {progreso['kg_embutidos']:.0f} kg | {progreso['kg_deben_embutir']:.0f} kg ({progreso['porcentaje']:.1f}%)</b>",
                    xref="paper", yref="paper",
                    x=0.74, y=1.13,  # Posición
                    showarrow=False,
                    font=dict(size=22, color="#000000"),  # Texto 
                    xanchor="center"
                ),
                
            ],
            # Shapes para crear la barra de progreso visual
            shapes=[
                # Fondo gris de la barra (100% del espacio) - MAS GRANDE Y ANCHA - BAJADA
                dict(
                    type="rect",
                    xref="paper", yref="paper",
                    x0=0.50, y0=1.07,  # Posicion
                    x1=0.98, y1=1.13,  # Posicion
                    fillcolor="rgba(200, 200, 200, 0.4)",  # Gris claro
                    line=dict(color="#0c1fc2", width=2)
                ),
                # Barra llena - COLOR DINÁMICO SEGÚN PORCENTAJE
                dict(
                    type="rect",
                    xref="paper", yref="paper",
                    x0=0.50, y0=1.07,  # Mismo inicio que el fondo - bajada
                    x1=0.50 + (0.48 * min(progreso['porcentaje'], 100) / 100),  # Se llena proporcionalmente (más ancha)
                    y1=1.13,  # Misma altura que el fondo - bajada
                    fillcolor=(
                        "rgba(248, 240, 0, 0.94)" if progreso['porcentaje'] <= 50 else  # AMARILLO 1-50%
                        "rgba(76, 233, 14, 0.97)" if progreso['porcentaje'] <= 89 else  # VERDE 51-89%
                        "rgba(248, 163, 0, 1)" if progreso['porcentaje'] <= 100 else    # NARANJA 90-100%
                        "rgba(248, 0, 0, 0.94)"  # ROJO 101%+
                    ),
                    line=dict(color="#0c1fc2", width=0)
                )
            ],
            xaxis=dict(
                title=dict(text='<b>Fecha y Hora</b>', font=dict(size=24)),
                showgrid=True,
                gridcolor='lightgray',
                gridwidth=2,
                tickfont=dict(size=15),  # Texto mas grande
                showline=True,
                linecolor='black',
                linewidth=2
            ),
            yaxis=dict(
                title=dict(text='<b>Peso Sauciso (kg)</b>' , font=dict(size=24)),
                showgrid=True,
                gridcolor='lightgray',
                gridwidth=2,
                tickfont=dict(size=15),  # Texto más grande
                showline=True,
                linecolor='black',
                linewidth=2,
                # Rango automático simple
                range=[0, df_peso_sauciso['_PesoSauciso'].max() * 1.2]
            ),
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=825,  # Altura mayor para pantalla completa
            margin=dict(t=80, b=150, l=100, r=60),
            dragmode='pan',
            showlegend=True,
            legend=dict(
                x=0.02,
                y=0.98,
                bgcolor='rgba(255, 255, 255, 0.8)',
                font=dict(size=16)
            )
        )
        
        # Mostrar el grafico optimizado para TV
        st.plotly_chart(fig, use_container_width=True, config={
            'displayModeBar': False,  # Sin barra de herramientas para TV
            'displaylogo': False,
            'scrollZoom': False
        }, key=f"grafico_{codigo_actual}_{odp_actual}")  # Clave única para evitar duplicación

def dashboard_peso_embuticion():
    """Dashboard específico para Peso Embutición - Tabla Peso Sauciso"""
    
    # Titulo del dashboard 
    st.title("Peso sauciso")
    
    # Verificar conexion
    if not verificar_conexion():
        st.error("No hay conexión a la base de datos. No se pueden cargar los datos.")
        return

    # Inicializar session_state para persistencia de filtros
    if 'peso_ano_seleccionado' not in st.session_state:
        st.session_state.peso_ano_seleccionado = '2025'  # Valor por defecto
    if 'peso_semana_seleccionada' not in st.session_state:
        st.session_state.peso_semana_seleccionada = 'Todas'
    if 'peso_dia_seleccionado' not in st.session_state:
        st.session_state.peso_dia_seleccionado = 'Todas'
    if 'peso_codigo_seleccionado' not in st.session_state:
        st.session_state.peso_codigo_seleccionado = 'Todas'
    if 'peso_odp_seleccionado' not in st.session_state:
        st.session_state.peso_odp_seleccionado = 'Todas'
    if 'modo_pantalla_completa' not in st.session_state:
        st.session_state.modo_pantalla_completa = False

    # Control de auto-refresh desde session state
    auto_refresh = st.session_state.get('auto_refresh', False)
    refresh_interval = st.session_state.get('refresh_interval', 60)  # 60 segundos por defecto
    
    # Mostrar estado de actualización
    if auto_refresh:
        # Calcular tiempo restante
        last_update = st.session_state.get('last_update_time', datetime.now())
        time_elapsed = (datetime.now() - last_update).total_seconds()
        time_remaining = max(0, refresh_interval - time_elapsed)
        
        if time_remaining > 0:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.success(f"🔄 **Actualización automática ACTIVA** - Cada {refresh_interval} segundos")
        else:
            st.success("🔄 **Actualizando datos...**")
            st.session_state['last_update_time'] = datetime.now()
            time.sleep(1)
            st.rerun()
    else:
        st.info("⏸️ **Actualización automática DESACTIVADA** - Solo manual")
    
    st.markdown("---")
    
    # Filtros de segmentacion
    st.subheader("Tiempo")
    
    # Crear tres columnas para los filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**Año**")
        # Obtener años disponibles
        query_anos = """
        SELECT DISTINCT YEAR(FECHAINGRESO) as Año
        FROM vwRegistrosDetallados 
        WHERE FECHAINGRESO IS NOT NULL
        ORDER BY Año DESC
        """
        df_anos, _ = consultar_datos(query_anos)
        
        if df_anos is not None and not df_anos.empty:
            anos_disponibles = ['Todas'] + [str(int(año)) for año in df_anos['Año'].tolist()]
            
            # Usar el valor guardado en session_state si existe en las opciones disponibles
            if st.session_state.peso_ano_seleccionado in anos_disponibles:
                index_default = anos_disponibles.index(st.session_state.peso_ano_seleccionado)
            else:
                index_default = 1 if '2025' in anos_disponibles else 0
                st.session_state.peso_ano_seleccionado = anos_disponibles[index_default]
            
            año_seleccionado = st.selectbox("", anos_disponibles, index=index_default, key="año")
            
            # Actualizar session_state cuando el usuario cambie la selección
            if año_seleccionado != st.session_state.peso_ano_seleccionado:
                st.session_state.peso_ano_seleccionado = año_seleccionado
                # Resetear filtros dependientes cuando cambia el año
                st.session_state.peso_semana_seleccionada = 'Todas'
                st.session_state.peso_dia_seleccionado = 'Todas'
                st.session_state.peso_codigo_seleccionado = 'Todas'
                st.session_state.peso_odp_seleccionado = 'Todas'
                st.rerun()
        else:
            año_seleccionado = 'Todas'
    
    with col2:
        st.write("**Semana**")
        # Obtener semanas disponibles para el año seleccionado
        if año_seleccionado != 'Todas':
            query_semanas = f"""
            SELECT DISTINCT DATEPART(week, FECHAINGRESO) as Semana
            FROM vwRegistrosDetallados 
            WHERE YEAR(FECHAINGRESO) = {año_seleccionado}
            AND FECHAINGRESO IS NOT NULL
            ORDER BY Semana
            """
        else:
            query_semanas = """
            SELECT DISTINCT DATEPART(week, FECHAINGRESO) as Semana
            FROM vwRegistrosDetallados 
            WHERE FECHAINGRESO IS NOT NULL
            ORDER BY Semana
            """
        
        df_semanas, _ = consultar_datos(query_semanas)
        
        if df_semanas is not None and not df_semanas.empty:
            semanas_disponibles = ['Todas'] + [str(int(sem)) for sem in df_semanas['Semana'].tolist()]
            
            # Usar el valor guardado en session_state si existe en las opciones disponibles
            if st.session_state.peso_semana_seleccionada in semanas_disponibles:
                index_default = semanas_disponibles.index(st.session_state.peso_semana_seleccionada)
            else:
                index_default = 0  # 'Todas'
                st.session_state.peso_semana_seleccionada = 'Todas'
            
            semana_seleccionada = st.selectbox("", semanas_disponibles, index=index_default, key="semana")
            
            # Actualizar session_state cuando el usuario cambie la seleccion
            if semana_seleccionada != st.session_state.peso_semana_seleccionada:
                st.session_state.peso_semana_seleccionada = semana_seleccionada
                # Resetear filtros dependientes cuando cambia la semana
                st.session_state.peso_dia_seleccionado = 'Todas'
                st.session_state.peso_codigo_seleccionado = 'Todas'
                st.session_state.peso_odp_seleccionado = 'Todas'
                st.rerun()
        else:
            semana_seleccionada = 'Todas'
    
    with col3:
        st.write("**Día**")
        # Obtener días disponibles basado en selecciones anteriores
        condiciones_dia = ["FECHAINGRESO IS NOT NULL"]
        
        if año_seleccionado != 'Todas':
            condiciones_dia.append(f"YEAR(FECHAINGRESO) = {año_seleccionado}")
        
        if semana_seleccionada != 'Todas':
            condiciones_dia.append(f"DATEPART(week, FECHAINGRESO) = {semana_seleccionada}")
        
        where_dia = " AND ".join(condiciones_dia)
        
        query_dias = f"""
        SELECT DISTINCT DATENAME(weekday, FECHAINGRESO) as Nom_dia
        FROM vwRegistrosDetallados 
        WHERE {where_dia}
        ORDER BY 
            CASE DATENAME(weekday, FECHAINGRESO)
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
                WHEN 'Saturday' THEN 6
                WHEN 'Sunday' THEN 7
            END
        """
        
        df_dias, _ = consultar_datos(query_dias)
        
        if df_dias is not None and not df_dias.empty:
            # Mapear dias de ingles a español
            dias_map = {
                'Monday': 'lunes',
                'Tuesday': 'martes', 
                'Wednesday': 'miércoles',
                'Thursday': 'jueves',
                'Friday': 'viernes',
                'Saturday': 'sábado',
                'Sunday': 'domingo'
            }
            
            dias_disponibles_es = ['Todas'] + [dias_map.get(dia, dia) for dia in df_dias['Nom_dia'].tolist()]
        else:
            # Si no hay datos disponibles, mostrar todos los días
            dias_disponibles_es = ['Todas', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        
        # Usar el valor guardado en session_state si existe en las opciones disponibles
        if st.session_state.peso_dia_seleccionado in dias_disponibles_es:
            index_default = dias_disponibles_es.index(st.session_state.peso_dia_seleccionado)
        else:
            index_default = 0  # 'Todas'
            st.session_state.peso_dia_seleccionado = 'Todas'
        
        dia_seleccionado = st.selectbox("", dias_disponibles_es, index=index_default, key="dia")
        
        # Actualizar session_state cuando el usuario cambie la seleccion
        if dia_seleccionado != st.session_state.peso_dia_seleccionado:
            st.session_state.peso_dia_seleccionado = dia_seleccionado
            # Resetear filtros dependientes cuando cambia el dia
            st.session_state.peso_codigo_seleccionado = 'Todas'
            st.session_state.peso_odp_seleccionado = 'Todas'
            st.rerun()
    
    # Filtros adicionales
    st.subheader("Filtros")
    
    # Crear dos columnas para los nuevos filtros
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Por CÓDIGO**")
        # Obtener codigos disponibles basado en selecciones de tiempo
        condiciones_codigo = ["FECHAINGRESO IS NOT NULL", "CODIGO IS NOT NULL", "CODIGO != ''"]
        
        if año_seleccionado != 'Todas':
            condiciones_codigo.append(f"YEAR(FECHAINGRESO) = {año_seleccionado}")
        
        if semana_seleccionada != 'Todas':
            condiciones_codigo.append(f"DATEPART(week, FECHAINGRESO) = {semana_seleccionada}")
        
        if dia_seleccionado != 'Todas':
            dias_map_reverse = {
                'lunes': 'Monday',
                'martes': 'Tuesday', 
                'miércoles': 'Wednesday',
                'jueves': 'Thursday',
                'viernes': 'Friday',
                'sábado': 'Saturday',
                'domingo': 'Sunday'
            }
            dia_ingles = dias_map_reverse.get(dia_seleccionado, dia_seleccionado)
            condiciones_codigo.append(f"DATENAME(weekday, FECHAINGRESO) = '{dia_ingles}'")
        
        where_codigo = " AND ".join(condiciones_codigo)
        
        query_codigos = f"""
        SELECT DISTINCT CODIGO
        FROM vwRegistrosDetallados 
        WHERE {where_codigo}
        ORDER BY CODIGO
        """
        df_codigos, _ = consultar_datos(query_codigos)
        
        if df_codigos is not None and not df_codigos.empty:
            codigos_disponibles = ['Todas'] + df_codigos['CODIGO'].tolist()
            
            # Campo de busqueda para codigos
            buscar_codigo = st.text_input("🔍 Buscar código:", key="buscar_codigo", 
                                        placeholder="Escriba para buscar...")

            # Filtrar codigos segun busqueda
            if buscar_codigo:
                codigos_filtrados = ['Todas'] + [c for c in df_codigos['CODIGO'].tolist() 
                                               if buscar_codigo.upper() in c.upper()]
                if len(codigos_filtrados) > 1:
                    codigos_disponibles = codigos_filtrados
            
            # Determinar indice por defecto para session_state
            try:
                index_default = codigos_disponibles.index(st.session_state.peso_codigo_seleccionado) if st.session_state.peso_codigo_seleccionado in codigos_disponibles else 0
            except:
                index_default = 0
            
            codigo_seleccionado = st.selectbox("", codigos_disponibles, 
                                             index=index_default, key="select_codigo")
            
            # Actualizar session_state y resetear filtros dependientes si cambio
            if codigo_seleccionado != st.session_state.peso_codigo_seleccionado:
                st.session_state.peso_codigo_seleccionado = codigo_seleccionado
                # Resetear ODP al cambiar código
                st.session_state.peso_odp_seleccionado = 'Todas'
        else:
            codigo_seleccionado = 'Todas'
    
    with col2:
        st.write("**Por ODP**")
        # Obtener ODPs disponibles basado en selecciones anteriores
        condiciones_odp = ["FECHAINGRESO IS NOT NULL", "ODP IS NOT NULL", "ODP != ''"]
        
        if año_seleccionado != 'Todas':
            condiciones_odp.append(f"YEAR(FECHAINGRESO) = {año_seleccionado}")
        
        if semana_seleccionada != 'Todas':
            condiciones_odp.append(f"DATEPART(week, FECHAINGRESO) = {semana_seleccionada}")
        
        if dia_seleccionado != 'Todas':
            dias_map_reverse = {
                'lunes': 'Monday',
                'martes': 'Tuesday', 
                'miércoles': 'Wednesday',
                'jueves': 'Thursday',
                'viernes': 'Friday',
                'sábado': 'Saturday',
                'domingo': 'Sunday'
            }
            dia_ingles = dias_map_reverse.get(dia_seleccionado, dia_seleccionado)
            condiciones_odp.append(f"DATENAME(weekday, FECHAINGRESO) = '{dia_ingles}'")
        
        if codigo_seleccionado != 'Todas':
            condiciones_odp.append(f"CODIGO = '{codigo_seleccionado}'")
        
        where_odp = " AND ".join(condiciones_odp)
        
        # MEJORADO: Buscar ODPs tanto en registros como en órdenes disponibles
        query_odps = f"""
        WITH ODPsDeRegistros AS (
            -- ODPs que YA tienen registros de producción (aplicando filtros)
            SELECT DISTINCT ODP
            FROM vwRegistrosDetallados 
            WHERE {where_odp}
        ),
        ODPsDeOrdenes AS (
            -- ODPs de órdenes que existen (aplicando filtros de código si está seleccionado)
            SELECT DISTINCT od.CodigoOrden as ODP
            FROM vwOrdenDocumento od
            WHERE 1=1
                {f"AND od.CodigoProducto = '{codigo_seleccionado}'" if codigo_seleccionado != 'Todas' else ''}
        )
        SELECT DISTINCT ODP 
        FROM (
            SELECT ODP FROM ODPsDeRegistros
            UNION
            SELECT ODP FROM ODPsDeOrdenes
        ) AS TodosODPs
        WHERE ODP IS NOT NULL AND ODP != ''
        ORDER BY ODP
        """
        df_odps, _ = consultar_datos(query_odps)
        
        if df_odps is not None and not df_odps.empty:
            odps_disponibles = ['Todas'] + df_odps['ODP'].tolist()
            
            # Campo de busqueda para ODPs
            buscar_odp = st.text_input("🔍 Buscar ODP:", key="buscar_odp", 
                                     placeholder="Escriba para buscar...")
            
            # Filtrar ODPs según busqueda
            if buscar_odp:
                odps_filtrados = ['Todas'] + [o for o in df_odps['ODP'].tolist() 
                                             if buscar_odp.upper() in o.upper()]
                if len(odps_filtrados) > 1:
                    odps_disponibles = odps_filtrados
            
            # Determinar indice por defecto para session_state
            try:
                index_default = odps_disponibles.index(st.session_state.peso_odp_seleccionado) if st.session_state.peso_odp_seleccionado in odps_disponibles else 0
            except:
                index_default = 0
            
            odp_seleccionado = st.selectbox("", odps_disponibles, 
                                          index=index_default, key="select_odp")
            
            # Actualizar session_state si cambio
            if odp_seleccionado != st.session_state.peso_odp_seleccionado:
                st.session_state.peso_odp_seleccionado = odp_seleccionado
        else:
            odp_seleccionado = 'Todas'
    
    # Mostrar filtros aplicados 
    st.markdown("---")
    filtros_aplicados = []
    if año_seleccionado != 'Todas':
        filtros_aplicados.append(f"**Año:** {año_seleccionado}")
    if semana_seleccionada != 'Todas':
        filtros_aplicados.append(f"**Semana:** {semana_seleccionada}")
    if dia_seleccionado != 'Todas':
        filtros_aplicados.append(f"**Día:** {dia_seleccionado}")
    if codigo_seleccionado != 'Todas':
        filtros_aplicados.append(f"**Código:** {codigo_seleccionado}")
    if odp_seleccionado != 'Todas':
        filtros_aplicados.append(f"**ODP:** {odp_seleccionado}")
    
    if filtros_aplicados:
        st.write("🔍 **Filtros aplicados:** " + " | ".join(filtros_aplicados))
    else:
        st.write("📊 **Mostrando:** Todos los datos disponibles")
    
    st.markdown("---")
    
    
    # Construir condiciones WHERE basadas en los filtros
    condiciones_where = ["FECHAINGRESO IS NOT NULL", "PESONETO IS NOT NULL", "NUMEMBALAJE IS NOT NULL", "NUMEMBALAJE > 0"]
    
    if año_seleccionado != 'Todas':
        condiciones_where.append(f"YEAR(FECHAINGRESO) = {año_seleccionado}")
    
    if semana_seleccionada != 'Todas':
        condiciones_where.append(f"DATEPART(week, FECHAINGRESO) = {semana_seleccionada}")
    
    if dia_seleccionado != 'Todas':
        # Mapear dias en español a ingles para SQL Server
        dias_map = {
            'lunes': 'Monday',
            'martes': 'Tuesday', 
            'miércoles': 'Wednesday',
            'jueves': 'Thursday',
            'viernes': 'Friday',
            'sábado': 'Saturday',
            'domingo': 'Sunday'
        }
        dia_ingles = dias_map.get(dia_seleccionado, dia_seleccionado)
        condiciones_where.append(f"DATENAME(weekday, FECHAINGRESO) = '{dia_ingles}'")
    
    if codigo_seleccionado != 'Todas':
        condiciones_where.append(f"CODIGO = '{codigo_seleccionado}'")
    
    if odp_seleccionado != 'Todas':
        condiciones_where.append(f"ODP = '{odp_seleccionado}'")
    
    where_clause = " AND ".join(condiciones_where)
    
    # Determinar si incluir ODP en la consulta (cuando se ha filtrado por una ODP específica)
    incluir_odp = odp_seleccionado != 'Todas'
    
    # Consulta SQL que replica las formulas DAX con filtros aplicados
    if incluir_odp:
        # Incluir ODP cuando se ha filtrado por una ODP específica
        query_peso_sauciso = f"""
        WITH DatosEmbuticion AS (
            SELECT 
                FECHAINGRESO,
                PESONETO,
                NUMEMBALAJE,
                PROCESO,
                CODIGO,
                ODP
            FROM vwRegistrosDetallados 
            WHERE {where_clause}
        ),
        KgEmbutidos AS (
            SELECT 
                FECHAINGRESO,
                CODIGO,
                ODP,
                SUM(CASE WHEN PROCESO = 'Embutición' THEN PESONETO ELSE 0 END) as _kgEmbutidos,
                SUM(NUMEMBALAJE) as TotalEmbalajes
            FROM DatosEmbuticion
            GROUP BY FECHAINGRESO, CODIGO, ODP
        )
        SELECT 
            FECHAINGRESO,
            CODIGO,
            ODP,
            _kgEmbutidos,
            TotalEmbalajes,
            CASE 
                WHEN TotalEmbalajes > 0 THEN _kgEmbutidos / TotalEmbalajes 
                ELSE 0 
            END as _PesoSauciso
        FROM KgEmbutidos
        WHERE _kgEmbutidos > 0
        ORDER BY FECHAINGRESO ASC
        """
    else:
        # Consulta original sin ODP cuando no hay filtro específico de ODP
        query_peso_sauciso = f"""
        WITH DatosEmbuticion AS (
            SELECT 
                FECHAINGRESO,
                PESONETO,
                NUMEMBALAJE,
                PROCESO,
                CODIGO,
                ODP
            FROM vwRegistrosDetallados 
            WHERE {where_clause}
        ),
        KgEmbutidos AS (
            SELECT 
                FECHAINGRESO,
                CODIGO,
                SUM(CASE WHEN PROCESO = 'Embutición' THEN PESONETO ELSE 0 END) as _kgEmbutidos,
                SUM(NUMEMBALAJE) as TotalEmbalajes
            FROM DatosEmbuticion
            GROUP BY FECHAINGRESO, CODIGO
        )
        SELECT 
            FECHAINGRESO,
            CODIGO,
            _kgEmbutidos,
            TotalEmbalajes,
            CASE 
                WHEN TotalEmbalajes > 0 THEN _kgEmbutidos / TotalEmbalajes 
                ELSE 0 
            END as _PesoSauciso
        FROM KgEmbutidos
        WHERE _kgEmbutidos > 0
        ORDER BY FECHAINGRESO ASC
        """
    
    # Cargar datos
    df_peso_sauciso, error = consultar_datos(query_peso_sauciso)
    
    if error:
        st.error(f"Error al cargar datos: {error}")
        return

    if df_peso_sauciso is None or df_peso_sauciso.empty:
        st.warning("No se encontraron datos")
        return

    # Ordenar por fecha para el grafico
    df_peso_sauciso = df_peso_sauciso.sort_values('FECHAINGRESO')
    
    # Obtener el ultimo codigo registrado DE LOS DATOS QUE TIENEN PESO SAUCISO
    ultimo_codigo = "Sin datos"
    if not df_peso_sauciso.empty:
        # Obtener el ultimo codigo directamente de los datos calculados de peso sauciso
        # Esto asegura que el codigo tenga datos reales para mostrar
        query_ultimo_codigo_peso = f"""
        WITH DatosEmbuticion AS (
            SELECT 
                FECHAINGRESO,
                PESONETO,
                NUMEMBALAJE,
                PROCESO,
                CODIGO,
                ODP
            FROM vwRegistrosDetallados 
            WHERE {where_clause}
        ),
        KgEmbutidos AS (
            SELECT 
                FECHAINGRESO,
                CODIGO,
                SUM(CASE WHEN PROCESO = 'Embutición' THEN PESONETO ELSE 0 END) as _kgEmbutidos,
                SUM(NUMEMBALAJE) as TotalEmbalajes
            FROM DatosEmbuticion
            GROUP BY FECHAINGRESO, CODIGO
        ),
        PesoSauciso AS (
            SELECT 
                FECHAINGRESO,
                CODIGO,
                _kgEmbutidos,
                TotalEmbalajes,
                CASE 
                    WHEN TotalEmbalajes > 0 THEN _kgEmbutidos / TotalEmbalajes 
                    ELSE 0 
                END as _PesoSauciso
            FROM KgEmbutidos
            WHERE _kgEmbutidos > 0
        )
        SELECT TOP 1 CODIGO, FECHAINGRESO
        FROM PesoSauciso
        WHERE CODIGO IS NOT NULL 
            AND CODIGO != ''
        ORDER BY FECHAINGRESO DESC
        """
        try:
            df_ultimo, _ = consultar_datos(query_ultimo_codigo_peso)
            if df_ultimo is not None and not df_ultimo.empty and df_ultimo.iloc[0]['CODIGO'] is not None:
                ultimo_codigo = df_ultimo.iloc[0]['CODIGO']
            else:
                # Fallback: consulta mas simple para obtener ultimo codigo con datos
                query_simple = f"""
                SELECT TOP 1 CODIGO 
                FROM vwRegistrosDetallados 
                WHERE {where_clause}
                    AND PROCESO = 'Embutición'
                    AND CODIGO IS NOT NULL 
                    AND CODIGO != ''
                    AND PESONETO > 0
                ORDER BY FECHAINGRESO DESC
                """
                df_simple, _ = consultar_datos(query_simple)
                if df_simple is not None and not df_simple.empty:
                    ultimo_codigo = df_simple.iloc[0]['CODIGO']
        except Exception as e:
            st.error(f"Error al obtener ultimo codigo: {e}")
            # Fallback final: consulta mas simple aun
            try:
                query_fallback = f"""
                SELECT TOP 1 CODIGO 
                FROM vwRegistrosDetallados 
                WHERE {where_clause}
                    AND CODIGO IS NOT NULL 
                    AND CODIGO != ''
                ORDER BY FECHAINGRESO DESC
                """
                df_fallback, _ = consultar_datos(query_fallback)
                if df_fallback is not None and not df_fallback.empty:
                    ultimo_codigo = df_fallback.iloc[0]['CODIGO']
                else:
                    ultimo_codigo = "Sin datos"
            except:
                ultimo_codigo = "Sin datos"
    
    
    # Botones de visualizacion
    col_btn1, col_btn2 = st.columns([1, 4])
    
    with col_btn1:
        pantalla_completa = st.button("🖥️ Pantalla Completa", use_container_width=True)
    
    # Mostrar vista segun el modo seleccionado
    if pantalla_completa or st.session_state.get('modo_pantalla_completa', False):
        st.session_state['modo_pantalla_completa'] = True
        mostrar_vista_pantalla_completa(df_peso_sauciso, ultimo_codigo, where_clause)
    else:
        st.session_state['modo_pantalla_completa'] = False
        # Debug temporal para verificar qué codigo se detecto (solo en vista normal)
        if ultimo_codigo != "Sin datos":
            st.info(f"🔍 Último código detectado: **{ultimo_codigo}**")
        else:
            st.warning("⚠️ No se pudo detectar último código con datos válidos")
        mostrar_vista_normal(df_peso_sauciso)
    
    # Auto-refresh si esta activado
    if auto_refresh:
        # En vista normal mostrar contador, en pantalla completa solo actualizar silenciosamente
        if not st.session_state.get('modo_pantalla_completa', False):
            # Vista normal: mostrar contador
            placeholder = st.empty()
            for i in range(refresh_interval, 0, -1):
                placeholder.info(f"⏱️ Próxima actualización en: **{i} segundos**")
                time.sleep(1)
            placeholder.empty()
        else:
            # Pantalla completa: actualizar cada 1 segundo para alternancia suave
            time.sleep(1)
        st.rerun()
