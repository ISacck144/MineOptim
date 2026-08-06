"""
Dashboard APU — Pantalla viva de despacho minero.

Lo no negociable: dos contadores de toneladas subiendo a distinta velocidad.
Un jurado entiende esa imagen en 3 segundos sin leer una ecuación.

Ejecución:
  cd /home/karla/apu-dispatch
  PYTHONPATH=src streamlit run dashboard/app.py

Datos sintéticos — no corresponden a ninguna mina real.
"""

import os
import sys
import time
import copy

import streamlit as st

_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
if _src not in sys.path:
    sys.path.insert(0, _src)

from apu.sim.engine import MotorSimulacion, cargar_config
from apu.dispatch.baselines import FixedGroup
from apu.dispatch.hungarian import HungarianDispatcher
from apu.sim.events import GestorEventos
from apu.dispatch.lp_flow import LPFlowPlanner
from apu.ml.residual_model import ResidualForestModel
from apu.sim.dump import TipoDestino
from apu.metrics.match_factor import calcular_match_factor
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# Configuración de página
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="APU — Despacho Minero",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')


@st.cache_data
def _cargar_config(nombre: str) -> dict:
    return cargar_config(os.path.join(_CONFIG_DIR, f'{nombre}.yaml'))


def _asignaciones_fg(config: dict) -> dict:
    palas = [p['id'] for p in config['palas']]
    camiones = [c['id'] for c in config['camiones']]
    return {c: palas[i % len(palas)] for i, c in enumerate(camiones)}


def _crear_engine(config: dict, dispatcher, v2_cfg: dict, seed: int,
                  lp_activo: bool = False) -> MotorSimulacion:
    """Crea y prepara un engine CON GestorEventos, listo para avanzar paso a paso."""
    import simpy

    cfg_v3 = config.get('v3', v2_cfg)  # v3 hereda config de v2 si no existe v3

    gestor_ev = GestorEventos(cfg_v3, rng=np.random.default_rng(seed + 1))
    lp_plan   = LPFlowPlanner(config.get('planta', {})) if lp_activo else None
    ml_model  = ResidualForestModel(seed=seed) if cfg_v3.get('ml', {}).get('activado') else None

    engine = MotorSimulacion(config, dispatcher)
    engine._v2_cfg = cfg_v3
    engine._rng    = np.random.default_rng(seed)
    engine._gestor_ev = gestor_ev
    engine._lp_planner = lp_plan
    engine._ml_model   = ml_model
    engine._t_inicio_real = time.time()

    engine._construir_mina()

    # Lanzar procesos SimPy (ciclos de camiones + periódicos)
    for camion in engine.mine.camiones.values():
        engine.env.process(engine._ciclo_camion(camion))

    gestor_ev.iniciar(engine.env, engine.mine, engine.log_eventos)

    if lp_plan is not None:
        intervalo_lp = cfg_v3.get('despacho', {}).get('intervalo_pl_min', 30.0)
        engine.env.process(engine._proceso_lp(intervalo_lp))

    if ml_model is not None:
        burn_in = cfg_v3.get('ml', {}).get('burn_in_min', 120.0)
        engine.env.process(engine._proceso_ml_fit(burn_in))

    snap_int = cfg_v3.get('snapshot_intervalo_min', 10.0)
    engine.env.process(engine._proceso_snapshots(snap_int))

    return engine


def _ton_fino(engine: MotorSimulacion) -> float:
    return sum(
        d.toneladas_fino for d in engine.mine.destinos.values()
        if d.tipo == TipoDestino.CHANCADORA
    )


def _ton_chanc(engine: MotorSimulacion) -> float:
    return sum(
        d.toneladas_recibidas for d in engine.mine.destinos.values()
        if d.tipo == TipoDestino.CHANCADORA
    )


def _camiones_por_pala(engine: MotorSimulacion) -> dict[str, int]:
    conteo = {p: 0 for p in engine.mine.palas}
    for c in engine.mine.camiones.values():
        if c.shovel_asignada in conteo:
            conteo[c.shovel_asignada] += 1
    return conteo


def _eventos_recientes(engine: MotorSimulacion, n: int = 8) -> list[dict]:
    relevantes = [
        e for e in engine.log_eventos
        if e['tipo'] in ('falla_pala_programada', 'recuperacion_pala',
                         'bloqueo_via', 'desbloqueo_via', 'lp_solve', 'ml_fit')
    ]
    return relevantes[-n:]


# ─────────────────────────────────────────────────────────────────────────────
# Mapa de la mina (Plotly)
# ─────────────────────────────────────────────────────────────────────────────

def _mapa_mina(engine: MotorSimulacion, titulo: str):
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.info("plotly no instalado — mapa omitido")
        return

    red = engine.mine.red_vial
    coord = engine._coord_map

    fig = go.Figure()

    # Aristas (carreteras)
    if hasattr(red, 'aristas'):
        for a in red.aristas:
            nf = coord.get(a['from'], (0, 0))
            nt = coord.get(a['to'],   (0, 0))
            color = 'crimson' if engine.mine.red_vial._factores.get(
                (a['from'], a['to']), 1.0) >= 9000 else '#aaaaaa'
            fig.add_trace(go.Scatter(
                x=[nf[0], nt[0]], y=[nf[1], nt[1]],
                mode='lines',
                line=dict(color=color, width=3 if color == 'crimson' else 1.5),
                showlegend=False, hoverinfo='none',
            ))

    # Destinos
    for d in engine.mine.destinos.values():
        c = coord.get(d.id, (d.pos_x, d.pos_y))
        sym  = 'star'      if d.tipo == TipoDestino.CHANCADORA else 'triangle-up'
        col  = '#1f77b4'   if d.tipo == TipoDestino.CHANCADORA else '#8c564b'
        ton  = d.toneladas_recibidas
        fig.add_trace(go.Scatter(
            x=[c[0]], y=[c[1]], mode='markers+text',
            marker=dict(size=22, symbol=sym, color=col),
            text=[f'{d.id}<br>{ton:,.0f} t'], textposition='top center',
            name=d.id,
        ))

    # Palas
    for p in engine.mine.palas.values():
        c   = coord.get(p.id, (p.pos_x, p.pos_y))
        col = '#2ca02c' if p.operativa else '#d62728'
        lab = f'{p.id}<br>ley {p.ley_cu:.2f}%<br>{"⚙" if p.operativa else "⛔"}'
        fig.add_trace(go.Scatter(
            x=[c[0]], y=[c[1]], mode='markers+text',
            marker=dict(size=20, symbol='square', color=col),
            text=[lab], textposition='top center', name=p.id,
        ))

    # Camiones (posición aproximada = nodo actual)
    for cam in engine.mine.camiones.values():
        c = coord.get(cam.pos_actual, (0, 0))
        col = '#ff7f0e' if not cam.en_falla else '#aaaaaa'
        fig.add_trace(go.Scatter(
            x=[c[0] + np.random.uniform(-80, 80)],
            y=[c[1] + np.random.uniform(-80, 80)],
            mode='markers+text',
            marker=dict(size=11, symbol='circle', color=col),
            text=[cam.id], textposition='bottom center',
            name=cam.id,
        ))

    fig.update_layout(
        title=titulo,
        showlegend=False,
        height=370,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='#f8f9fa',
    )
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Gráfico de serie temporal
# ─────────────────────────────────────────────────────────────────────────────

def _grafico_series(snaps_fg: list, snaps_apu: list, t_falla: float):
    try:
        import plotly.graph_objects as go
    except ImportError:
        return
    if not snaps_fg and not snaps_apu:
        return

    fig = go.Figure()
    if snaps_fg:
        fig.add_trace(go.Scatter(
            x=[s['t_min'] for s in snaps_fg],
            y=[s['ton_fino'] for s in snaps_fg],
            name='FixedGroup', line=dict(color='#d62728', width=2),
        ))
    if snaps_apu:
        fig.add_trace(go.Scatter(
            x=[s['t_min'] for s in snaps_apu],
            y=[s['ton_fino'] for s in snaps_apu],
            name='APU', line=dict(color='#2ca02c', width=3, dash='dot'),
        ))
    fig.add_vline(x=t_falla, line_color='red', line_dash='dash',
                  annotation_text='Falla pala_2', annotation_position='top right')
    fig.update_layout(
        title='Ton. fino Cu acumulado',
        xaxis_title='t (min)', yaxis_title='ton fino',
        height=280, margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation='h', y=-0.2),
    )
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Layout principal
# ─────────────────────────────────────────────────────────────────────────────

st.title("APU — Asignación y Planificación Unificada")
st.caption("⚡ Motor de despacho camión-pala | Datos sintéticos generados por el simulador")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Configuración")
    config_name = st.selectbox("Escenario", ['mina_base', 'mina_andina'])
    seed        = st.number_input("Semilla aleatoria", value=42, step=1)
    speed       = st.select_slider(
        "Velocidad de simulación",
        options=[0.02, 0.05, 0.10, 0.20, 0.50],
        value=0.05,
        format_func=lambda v: f"{v:.2f} s/paso",
    )
    dt          = st.select_slider(
        "Paso de tiempo (min simulados)",
        options=[5, 10, 15, 30], value=10,
    )
    st.divider()
    btn_iniciar  = st.button("▶ Iniciar",  type="primary", use_container_width=True)
    btn_pausar   = st.button("⏸ Pausar",                   use_container_width=True)
    btn_reiniciar= st.button("↺ Reiniciar",                use_container_width=True)
    st.divider()
    st.caption("PERUMEC 2026 — Equipo APU")
    st.caption("Todos los datos son sintéticos")

# ── Session state ─────────────────────────────────────────────────────────────
ss = st.session_state

if btn_reiniciar:
    for k in list(ss.keys()):
        del ss[k]
    st.rerun()

config = _cargar_config(config_name)
duracion_min = config['simulacion']['duracion_horas'] * 60.0
v2_cfg = config.get('v3', config.get('v2', {}))

t_falla = 300.0
for ev in v2_cfg.get('eventos', {}).get('programados', []):
    if ev.get('tipo') == 'falla_pala':
        t_falla = ev.get('tiempo_min', 300.0)
        break

if btn_iniciar and 'engine_fg' not in ss:
    with st.spinner("Inicializando simulación..."):
        asig_fg = _asignaciones_fg(config)
        ss['engine_fg']  = _crear_engine(config, FixedGroup(asig_fg), v2_cfg, seed)
        ss['engine_apu'] = _crear_engine(
            config,
            HungarianDispatcher(
                lambda_acoplamiento=config.get('despacho', {}).get('lambda_acoplamiento', 0.5)
            ),
            v2_cfg, seed, lp_activo=True,
        )
        ss['t'] = 0.0
        ss['running'] = True

if btn_pausar:
    ss['running'] = False

# ── Métricas y visualización ──────────────────────────────────────────────────

# Barra de progreso
t_actual = ss.get('t', 0.0)
progreso = min(1.0, t_actual / duracion_min)
st.progress(progreso, text=f"t = {t_actual:.0f} / {duracion_min:.0f} min  ({progreso*100:.1f}%)")

# Encabezados de columnas
col_fg, col_apu = st.columns(2, gap="large")

with col_fg:
    st.subheader("FixedGroup  (baseline)")
    slot_fg_fino  = st.empty()
    slot_fg_mf    = st.empty()
    slot_fg_palas = st.empty()

with col_apu:
    st.subheader("APU  ★ sistema propuesto")
    slot_apu_fino  = st.empty()
    slot_apu_mf    = st.empty()
    slot_apu_palas = st.empty()

# Mapa y serie temporal
col_m1, col_m2 = st.columns(2)
slot_mapa_fg  = col_m1.empty()
slot_mapa_apu = col_m2.empty()

slot_serie    = st.empty()
slot_eventos  = st.empty()


def _render(engine_fg, engine_apu):
    tf = _ton_fino(engine_fg)
    ta = _ton_fino(engine_apu)
    delta_pct = (ta - tf) / tf * 100 if tf > 0 else 0.0

    with slot_fg_fino.container():
        st.metric("Ton. fino Cu", f"{tf:,.2f} t")
    with slot_fg_mf.container():
        mf = calcular_match_factor(engine_fg)
        st.metric("Match Factor", f"{mf:.3f}")
    with slot_fg_palas.container():
        cpf = _camiones_por_pala(engine_fg)
        st.caption("Camiones/pala: " + "  |  ".join(f"{k}: {v}" for k, v in cpf.items()))

    with slot_apu_fino.container():
        st.metric("Ton. fino Cu", f"{ta:,.2f} t",
                  delta=f"+{delta_pct:.1f}% vs FixedGroup" if delta_pct > 0 else f"{delta_pct:.1f}%")
    with slot_apu_mf.container():
        mf = calcular_match_factor(engine_apu)
        st.metric("Match Factor", f"{mf:.3f}")
    with slot_apu_palas.container():
        cpa = _camiones_por_pala(engine_apu)
        st.caption("Camiones/pala: " + "  |  ".join(f"{k}: {v}" for k, v in cpa.items()))

    with slot_mapa_fg.container():
        _mapa_mina(engine_fg, "FixedGroup — estado de la mina")
    with slot_mapa_apu.container():
        _mapa_mina(engine_apu, "APU — estado de la mina")

    with slot_serie.container():
        _grafico_series(engine_fg.snapshots, engine_apu.snapshots, t_falla)

    ev_fg  = _eventos_recientes(engine_fg,  5)
    ev_apu = _eventos_recientes(engine_apu, 5)
    with slot_eventos.container():
        st.subheader("Log de eventos recientes (APU)")
        if ev_apu:
            for e in reversed(ev_apu):
                icono = {'falla_pala_programada': '⚠️', 'recuperacion_pala': '✅',
                         'bloqueo_via': '🚧', 'desbloqueo_via': '🟢',
                         'lp_solve': '📊', 'ml_fit': '🤖'}.get(e['tipo'], 'ℹ️')
                st.caption(f"t={e['t']:6.1f} min  {icono}  {e['tipo'].replace('_', ' ')}")
        else:
            st.caption("Sin eventos aún...")


# ── Auto-avance ───────────────────────────────────────────────────────────────

if 'engine_fg' in ss and 'engine_apu' in ss:
    engine_fg  = ss['engine_fg']
    engine_apu = ss['engine_apu']
    t          = ss.get('t', 0.0)

    _render(engine_fg, engine_apu)

    if ss.get('running', False) and t < duracion_min:
        nueva_t = min(t + dt, duracion_min)
        engine_fg.env.run(until=nueva_t)
        engine_apu.env.run(until=nueva_t)
        ss['t'] = nueva_t

        time.sleep(speed)
        st.rerun()

    elif ss.get('running', False) and t >= duracion_min:
        ss['running'] = False
        tf  = _ton_fino(engine_fg)
        ta  = _ton_fino(engine_apu)
        pct = (ta - tf) / tf * 100 if tf > 0 else 0
        st.success(
            f"✅ Simulación completada — "
            f"APU: {ta:,.2f} t fino  |  FixedGroup: {tf:,.2f} t fino  "
            f"|  Brecha: +{pct:.1f}%"
        )

else:
    st.info(
        "Presiona **▶ Iniciar** en la barra lateral para arrancar la simulación.\n\n"
        "Verás dos contadores de toneladas de cobre fino subiendo a distinta velocidad — "
        "APU siempre arriba."
    )
