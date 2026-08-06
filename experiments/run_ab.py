"""
Experimento A/B para APU.
Corre uno o más despachadores sobre la misma configuración y semilla,
e imprime una tabla comparativa con los KPIs de cada uno.

Uso:
  PYTHONPATH=src python -m experiments.run_ab --version v0
  PYTHONPATH=src python -m experiments.run_ab --version v1
  PYTHONPATH=src python -m experiments.run_ab --version v1 --config mina_andina
  PYTHONPATH=src python -m experiments.run_ab --version v2
  PYTHONPATH=src python -m experiments.run_ab --version v2 --config mina_andina
"""

import argparse
import os
import sys

_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
if _src not in sys.path:
    sys.path.insert(0, _src)

from apu.sim.engine import MotorSimulacion, cargar_config
from apu.dispatch.baselines import ShortestQueue, Random, Nearest, SPTF, FixedGroup
from apu.dispatch.hungarian import HungarianDispatcher
from apu.metrics.kpis import calcular_kpis, imprimir_resumen, tabla_comparativa


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fixed_group_asignaciones(config: dict) -> dict:
    """Asigna camiones a palas en ciclo: c1→p1, c2→p2, c3→p3, c4→p1, ..."""
    palas_ids = [p['id'] for p in config['palas']]
    camiones_ids = [c['id'] for c in config['camiones']]
    return {c_id: palas_ids[i % len(palas_ids)] for i, c_id in enumerate(camiones_ids)}


def _correr_dispatcher(config: dict, dispatcher, duracion: float) -> dict:
    engine = MotorSimulacion(config, dispatcher)
    t_elapsed = engine.correr(duracion)
    return calcular_kpis(engine, t_elapsed)


def _guardar_png(resultados: list[dict], ruta: str, config_nombre: str, version: str = 'v1'):
    import matplotlib
    matplotlib.use('Agg')   # sin ventana gráfica (funciona sin display)
    import matplotlib.pyplot as plt
    import numpy as np

    nombres = [r['dispatcher'] for r in resultados]
    metricas = {
        'Ton. chancadora (t)':   [r['ton_chancadora'] for r in resultados],
        'Ton. fino Cu (t)':      [r['ton_fino'] for r in resultados],
        'Espera total (min)':    [r['tiempo_espera_total_min'] for r in resultados],
        'Match Factor':          [r['match_factor'] for r in resultados],
    }

    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    fig.suptitle(f'APU {version} — Comparativa de despachadores\n{config_nombre}', fontsize=13)
    colores = ['#d62728', '#ff7f0e', '#2ca02c', '#1f77b4', '#9467bd', '#8c564b']

    for ax, (titulo, valores) in zip(axes.flat, metricas.items()):
        barras = ax.bar(nombres, valores, color=colores[:len(nombres)], edgecolor='white')
        ax.set_title(titulo, fontsize=10, fontweight='bold')
        ax.set_xticks(range(len(nombres)))
        ax.set_xticklabels(nombres, rotation=30, ha='right', fontsize=8)
        ax.tick_params(axis='y', labelsize=8)
        # Etiquetar cada barra con su valor
        for barra, val in zip(barras, valores):
            ax.text(
                barra.get_x() + barra.get_width() / 2,
                barra.get_height() * 1.01,
                f'{val:,.1f}' if val > 10 else f'{val:.3f}',
                ha='center', va='bottom', fontsize=7
            )
        ax.grid(axis='y', alpha=0.3)
        # Resaltar la barra de APU
        if 'APU' in nombres:
            idx_apu = nombres.index('APU_Hungaro') if 'APU_Hungaro' in nombres else -1
            if idx_apu >= 0:
                barras[idx_apu].set_edgecolor('#FFD700')
                barras[idx_apu].set_linewidth(2.5)

    plt.tight_layout()
    plt.savefig(ruta, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  PNG guardado en: {ruta}")


# ─────────────────────────────────────────────────────────────────────────────
# v0
# ─────────────────────────────────────────────────────────────────────────────

def correr_v0(config: dict, duracion: float, seed: int):
    dispatcher = ShortestQueue()
    engine = MotorSimulacion(config, dispatcher)
    t_elapsed = engine.correr(duracion)
    kpis = calcular_kpis(engine, t_elapsed)
    imprimir_resumen(kpis, config_nombre=config.get('nombre', ''))

    assert t_elapsed < 10.0, (
        f"La simulación tardó {t_elapsed:.1f} s (límite: 10 s). "
        "Algo está muy mal en el motor SimPy."
    )
    print(f"\n  ✓ Criterio v0 cumplido: {t_elapsed:.3f} s < 10 s")


# ─────────────────────────────────────────────────────────────────────────────
# v1
# ─────────────────────────────────────────────────────────────────────────────

def correr_v1(config: dict, duracion: float, seed: int, config_nombre: str):
    asignaciones_fg = _fixed_group_asignaciones(config)

    despachadores = [
        ("Random",       Random(seed=seed)),
        ("Nearest",      Nearest()),
        ("ShortestQueue",ShortestQueue()),
        ("SPTF",         SPTF()),
        ("FixedGroup",   FixedGroup(asignaciones_fg)),
        ("APU_Hungaro",  HungarianDispatcher()),
    ]

    print(f"\n  Corriendo {len(despachadores)} despachadores "
          f"({duracion:.0f} h simuladas, semilla {seed})…\n")

    resultados = []
    for nombre, dispatcher in despachadores:
        kpis = _correr_dispatcher(config, dispatcher, duracion)
        resultados.append(kpis)
        print(f"  [{nombre:<16}] "
              f"chancadora={kpis['ton_chancadora']:>9,.0f} t  "
              f"fino={kpis['ton_fino']:>7,.2f} t  "
              f"espera={kpis['tiempo_espera_total_min']:>7,.1f} min  "
              f"MF={kpis['match_factor']:.3f}  "
              f"ADL={kpis['adl_ms']:.4f} ms")

    # ── Tabla completa ────────────────────────────────────────────────────────
    print()
    print("═" * 72)
    print("  TABLA COMPARATIVA — APU v1")
    print("═" * 72)
    print(f"  Config: {config_nombre}  |  Duración: {duracion:.0f} h  |  Semilla: {seed}")
    print()
    print(tabla_comparativa(resultados))
    print()

    # Comparar APU vs cada baseline — métrica principal: ton_fino (valor económico)
    apu = next(r for r in resultados if r['dispatcher'] == 'APU_Hungaro')
    baselines = [r for r in resultados if r['dispatcher'] != 'APU_Hungaro']
    mejor_baseline_fino = max(baselines, key=lambda r: r['ton_fino'])
    mejor_baseline_chca = max(baselines, key=lambda r: r['ton_chancadora'])

    delta_fino = apu['ton_fino'] - mejor_baseline_fino['ton_fino']
    pct_fino = delta_fino / mejor_baseline_fino['ton_fino'] * 100 if mejor_baseline_fino['ton_fino'] > 0 else 0
    delta_chca = apu['ton_chancadora'] - mejor_baseline_chca['ton_chancadora']
    pct_chca = delta_chca / mejor_baseline_chca['ton_chancadora'] * 100 if mejor_baseline_chca['ton_chancadora'] > 0 else 0

    print(f"  APU vs mejor baseline en ton.fino   ({mejor_baseline_fino['dispatcher']}): "
          f"{delta_fino:+,.2f} t  ({pct_fino:+.1f}%)")
    print(f"  APU vs mejor baseline en ton.chanc. ({mejor_baseline_chca['dispatcher']}): "
          f"{delta_chca:+,.0f} t  ({pct_chca:+.1f}%)")
    print("═" * 72)

    # ── PNG ───────────────────────────────────────────────────────────────────
    ruta_png = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'results', f'comparativa_v1_{config_nombre.replace(" ", "_")}.png'
    )
    try:
        _guardar_png(resultados, ruta_png, config_nombre)
    except ImportError:
        print("  (matplotlib no instalado — PNG omitido)")


# ─────────────────────────────────────────────────────────────────────────────
# v2
# ─────────────────────────────────────────────────────────────────────────────

def _correr_dispatcher_v2(config: dict, dispatcher, duracion: float,
                           v2_cfg: dict, seed: int) -> tuple[dict, list]:
    """
    Corre una simulación v2 con eventos, LP y ML.
    Retorna (kpis, snapshots).
    """
    from apu.sim.events import GestorEventos
    from apu.dispatch.lp_flow import LPFlowPlanner
    from apu.ml.residual_model import ResidualForestModel
    import numpy as np

    config_planta = config.get('planta', {})
    lp_cfg        = v2_cfg.get('despacho', config.get('despacho', {}))
    ml_cfg        = v2_cfg.get('ml', {})

    gestor_ev = GestorEventos(v2_cfg, rng=np.random.default_rng(seed + 1))
    lp_plan   = LPFlowPlanner(config_planta)
    ml_model  = ResidualForestModel(
        burn_in_samples=max(10, int(ml_cfg.get('burn_in_min', 120) / 10)),
        threshold=ml_cfg.get('threshold_degradacion', 0.15),
        seed=seed,
    ) if ml_cfg.get('activado', True) else None

    engine = MotorSimulacion(config, dispatcher)
    t_elapsed = engine.correr(
        duracion,
        v2_config     = v2_cfg,
        gestor_eventos= gestor_ev,
        lp_planner    = lp_plan,
        ml_model      = ml_model,
        seed          = seed,
    )
    kpis = calcular_kpis(engine, t_elapsed)
    kpis['eventos_log'] = [e for e in gestor_ev.log if 'falla' in e['tipo']]

    if ml_model and ml_model.alertas:
        kpis['ml_alertas'] = ml_model.alertas
        print(ml_model.resumen_alertas())

    return kpis, engine.snapshots


def _guardar_png_serie_temporal(series: dict, t_falla_min: float, ruta: str,
                                 config_nombre: str):
    """
    Genera la gráfica temporal de ton_fino acumulado.
    La línea vertical roja marca el instante de la falla de pala.
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    colores = ['#d62728', '#ff7f0e', '#2ca02c', '#1f77b4', '#9467bd', '#8c564b']
    grosor  = {'APU_Hungaro': 2.8}

    fig, ax = plt.subplots(figsize=(13, 6))

    for (nombre, snaps), color in zip(series.items(), colores):
        if not snaps:
            continue
        ts = [s['t_min'] for s in snaps]
        ys = [s['ton_fino'] for s in snaps]
        lw = grosor.get(nombre, 1.5)
        ax.plot(ts, ys, label=nombre, color=color, linewidth=lw,
                linestyle='--' if nombre == 'APU_Hungaro' else '-')

    ax.axvline(x=t_falla_min, color='red', linestyle=':', linewidth=1.8,
               label=f'Falla pala_2 (t={t_falla_min:.0f} min)')
    ax.axvspan(t_falla_min, t_falla_min + 90, alpha=0.08, color='red')

    ax.set_xlabel('Tiempo simulado (min)', fontsize=11)
    ax.set_ylabel('Ton. fino Cu acumulado (t)', fontsize=11)
    ax.set_title(
        f'APU v2 — Producción acumulada de cobre fino\n{config_nombre}\n'
        f'La brecha se ensancha después de la falla de pala_2 (t=300 min)',
        fontsize=11,
    )
    ax.legend(fontsize=9, loc='upper left')
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(ruta, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  PNG guardado en: {ruta}")


def correr_v2(config: dict, duracion: float, seed: int, config_nombre: str):
    v2_cfg = config.get('v2', {})
    asignaciones_fg = _fixed_group_asignaciones(config)

    despachadores = [
        ("Random",        Random(seed=seed)),
        ("Nearest",       Nearest()),
        ("ShortestQueue", ShortestQueue()),
        ("SPTF",          SPTF()),
        ("FixedGroup",    FixedGroup(asignaciones_fg)),
        ("APU_Hungaro",   HungarianDispatcher(
            lambda_acoplamiento=config.get('despacho', {}).get('lambda_acoplamiento', 0.5)
        )),
    ]

    # Instante de la falla programada (para la línea vertical del gráfico)
    t_falla = 300.0
    for ev in v2_cfg.get('eventos', {}).get('programados', []):
        if ev.get('tipo') == 'falla_pala':
            t_falla = ev.get('tiempo_min', 300.0)
            break

    print(f"\n  Corriendo {len(despachadores)} despachadores con eventos v2 "
          f"({duracion:.0f} h simuladas, semilla {seed})…")
    print(f"  Falla programada: pala_2 en t={t_falla:.0f} min\n")

    resultados = []
    series_temporales = {}

    for nombre, dispatcher in despachadores:
        kpis, snaps = _correr_dispatcher_v2(config, dispatcher, duracion, v2_cfg, seed)
        resultados.append(kpis)
        series_temporales[nombre] = snaps

        n_ev = len(kpis.get('eventos_log', []))
        print(f"  [{nombre:<16}] "
              f"chancadora={kpis['ton_chancadora']:>9,.0f} t  "
              f"fino={kpis['ton_fino']:>7,.2f} t  "
              f"espera={kpis['tiempo_espera_total_min']:>7,.1f} min  "
              f"MF={kpis['match_factor']:.3f}  "
              f"ADL={kpis['adl_ms']:.4f} ms  "
              f"eventos={n_ev}")

    # ── Tabla comparativa ─────────────────────────────────────────────────────
    print()
    print("═" * 72)
    print("  TABLA COMPARATIVA — APU v2 (con eventos aleatorios)")
    print("═" * 72)
    print(f"  Config: {config_nombre}  |  Duración: {duracion:.0f} h  |  Semilla: {seed}")
    print(f"  Falla pala_2 en t={t_falla:.0f} min  |  Reparación: 90 min")
    print()
    print(tabla_comparativa(resultados))
    print()

    apu = next(r for r in resultados if r['dispatcher'] == 'APU_Hungaro')
    baselines = [r for r in resultados if r['dispatcher'] != 'APU_Hungaro']
    mejor_bl = max(baselines, key=lambda r: r['ton_fino'])
    delta_fino = apu['ton_fino'] - mejor_bl['ton_fino']
    pct_fino   = delta_fino / mejor_bl['ton_fino'] * 100 if mejor_bl['ton_fino'] > 0 else 0
    print(f"  APU vs mejor baseline en ton.fino ({mejor_bl['dispatcher']}): "
          f"{delta_fino:+,.2f} t  ({pct_fino:+.1f}%)")
    print("═" * 72)

    dir_res = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')

    # ── PNG barras (misma lógica que v1) ─────────────────────────────────────
    ruta_barras = os.path.join(dir_res,
                               f'comparativa_v2_{config_nombre.replace(" ", "_")}.png')
    try:
        _guardar_png(resultados, ruta_barras, config_nombre, version='v2')
    except ImportError:
        print("  (matplotlib no instalado — PNG barras omitido)")

    # ── PNG serie temporal ────────────────────────────────────────────────────
    ruta_serie = os.path.join(dir_res,
                              f'serie_temporal_v2_{config_nombre.replace(" ", "_")}.png')
    try:
        _guardar_png_serie_temporal(series_temporales, t_falla, ruta_serie, config_nombre)
    except ImportError:
        print("  (matplotlib no instalado — PNG serie temporal omitido)")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='APU — Motor de despacho camión-pala para minería a tajo abierto'
    )
    parser.add_argument('--version', choices=['v0', 'v1', 'v2', 'v3'], default='v0')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--config', default='mina_base')
    parser.add_argument('--duracion', type=float, default=None,
                        help='Horas simuladas (sobreescribe el YAML)')
    args = parser.parse_args()

    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..', 'config', f'{args.config}.yaml'
    )
    if not os.path.exists(config_path):
        print(f"Error: no se encontró '{config_path}'")
        sys.exit(1)

    config = cargar_config(config_path)
    duracion = args.duracion or config['simulacion']['duracion_horas']
    config_nombre = config.get('nombre', args.config)

    print(f"\n  Iniciando APU — versión {args.version}")
    print(f"  Config: {args.config}.yaml  |  Duración: {duracion} h  |  Semilla: {args.seed}")

    if args.version == 'v0':
        correr_v0(config, duracion, args.seed)
    elif args.version == 'v1':
        correr_v1(config, duracion, args.seed, config_nombre)
    elif args.version == 'v2':
        correr_v2(config, duracion, args.seed, config_nombre)
    else:
        print(f"\n  La versión '{args.version}' aún no está implementada.")
        sys.exit(1)


if __name__ == '__main__':
    main()
