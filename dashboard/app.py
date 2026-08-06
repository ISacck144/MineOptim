"""
Dashboard Streamlit de APU — Pantalla partida.
Izquierda: despacho tradicional (FixedGroup).
Derecha: APU (despachador húngaro + PL).

Lo no negociable: dos contadores de toneladas subiendo a distinta velocidad.
Un jurado entiende esa imagen en 3 segundos sin leer una ecuación.

Se implementa en v2. Este archivo es el stub estructural.
Para correr: PYTHONPATH=src streamlit run dashboard/app.py
"""

import streamlit as st

st.set_page_config(
    page_title="APU — Despacho Minero",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("APU — Asignación y Planificación Unificada")
st.caption("Motor de despacho camión-pala para minería a tajo abierto")

col_izq, col_der = st.columns(2)

with col_izq:
    st.header("Despacho Tradicional")
    st.subheader("FixedGroup (camiones fijos a palas)")
    st.metric("Toneladas a chancadora", "—", help="Disponible desde v1")

with col_der:
    st.header("APU")
    st.subheader("Húngaro + Programación Lineal")
    st.metric("Toneladas a chancadora", "—", help="Disponible desde v2")

st.info(
    "Dashboard completo disponible en v2. "
    "Ejecuta `make v0` para ver la simulación por consola."
)
