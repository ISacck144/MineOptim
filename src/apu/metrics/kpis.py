"""
Cálculo y presentación de KPIs de una corrida de simulación.
"""


def calcular_kpis(engine, t_elapsed_real: float) -> dict:
    kpis = engine.resumen()
    kpis['t_elapsed_real_s'] = t_elapsed_real
    kpis['dispatcher'] = engine.dispatcher.nombre
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
    print(f"    Ton. brutas a chancadora : {kpis['ton_chancadora']:>12,.1f} t")
    print(f"    Ton. de fino (Cu) a planta: {kpis['ton_fino']:>11,.2f} t")
    print(f"    Ton. a botadero (desmonte): {kpis['ton_botadero']:>11,.1f} t")
    print(f"    Total transportado        : {kpis['ton_total']:>11,.1f} t")
    print(f"    Ciclos completados        : {kpis['ciclos_totales']:>11d}")
    print()
    print("  COLAS (tiempo perdido en ralentí)")
    print(f"    Espera total en palas : {kpis['tiempo_espera_total_min']:>10,.1f} min")
    print(f"    Promedio por ciclo    : {kpis['promedio_espera_por_ciclo_min']:>10.2f} min")
    print()
    print("  UTILIZACIÓN DE PALAS")
    for pala_id, util in kpis['utilizacion_palas'].items():
        barra = "█" * int(util / 5) + "░" * (20 - int(util / 5))
        print(f"    {pala_id:12s}: [{barra}] {util:5.1f}%")
    print()
    print(f"  Eventos en log   : {kpis['n_eventos_log']:>6d}")
    print(f"  Tiempo de ejecución real: {kpis['t_elapsed_real_s']:.3f} s")
    print(sep)
