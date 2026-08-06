"""
Cálculo y presentación de KPIs de una corrida de simulación.
"""

from .match_factor import calcular_match_factor


def calcular_kpis(engine, t_elapsed_real: float) -> dict:
    kpis = engine.resumen()
    kpis['t_elapsed_real_s'] = t_elapsed_real
    kpis['dispatcher'] = engine.dispatcher.nombre
    kpis['adl_ms'] = engine.dispatcher.adl_promedio_ms()
    kpis['match_factor'] = calcular_match_factor(engine)
    return kpis


def imprimir_resumen(kpis: dict, config_nombre: str = ""):
    dur_h = kpis['duracion_sim_min'] / 60.0
    sep = "═" * 58

    print()
    print(sep)
    print("  APU — RESUMEN DE SIMULACIÓN")
    print(sep)
    if config_nombre:
        print(f"  Configuración  : {config_nombre}")
    print(f"  Despachador    : {kpis['dispatcher']}")
    print(f"  Duración sim.  : {dur_h:.1f} h  ({kpis['duracion_sim_min']:.0f} min simulados)")
    print()
    print("  PRODUCCIÓN")
    print(f"    Ton. brutas a chancadora  : {kpis['ton_chancadora']:>12,.1f} t")
    print(f"    Ton. de fino (Cu) a planta: {kpis['ton_fino']:>12,.2f} t")
    print(f"    Ton. a botadero (desmonte): {kpis['ton_botadero']:>12,.1f} t")
    print(f"    Total transportado        : {kpis['ton_total']:>12,.1f} t")
    print(f"    Ciclos completados        : {kpis['ciclos_totales']:>12d}")
    print()
    print("  EFICIENCIA")
    print(f"    Match Factor          : {kpis['match_factor']:>10.3f}")
    print(f"    Espera total en palas : {kpis['tiempo_espera_total_min']:>10,.1f} min")
    print(f"    Promedio por ciclo    : {kpis['promedio_espera_por_ciclo_min']:>10.2f} min")
    print(f"    ADL (latencia decis.) : {kpis['adl_ms']:>10.4f} ms")
    print()
    print("  UTILIZACIÓN DE PALAS")
    for pala_id, util in kpis['utilizacion_palas'].items():
        barra = "█" * int(util / 5) + "░" * (20 - int(util / 5))
        print(f"    {pala_id:12s}: [{barra}] {util:5.1f}%")
    print()
    print(f"  Tiempo de ejecución real: {kpis['t_elapsed_real_s']:.3f} s")
    print(sep)


def tabla_comparativa(resultados: list[dict]) -> str:
    """Genera una tabla de texto comparando múltiples despachadores."""
    encabezado = (
        f"{'Despachador':<16} {'Ton.Chanca':>10} {'Ton.Fino':>9} "
        f"{'Espera(min)':>11} {'MatchFact':>9} {'ADL(ms)':>8}"
    )
    linea = "─" * len(encabezado)
    filas = [encabezado, linea]

    for r in resultados:
        fila = (
            f"{r['dispatcher']:<16} "
            f"{r['ton_chancadora']:>10,.0f} "
            f"{r['ton_fino']:>9,.2f} "
            f"{r['tiempo_espera_total_min']:>11,.1f} "
            f"{r['match_factor']:>9.3f} "
            f"{r['adl_ms']:>8.4f}"
        )
        filas.append(fila)

    return "\n".join(filas)
