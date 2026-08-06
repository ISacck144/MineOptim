"""
Match Factor (MF): razón entre la capacidad real de la flota y
la capacidad de servicio de las palas.

Fórmula (Alarie & Gamache, 2002; Atkinson, 1992):
  MF = N_trucks × T_carga_prom / (N_palas_activas × T_ciclo_prom)

Donde:
  T_ciclo_prom = duración_sim × N_trucks / ciclos_totales
  T_carga_prom = Σ_shovels(t_carga_s × n_cargas_s) / ciclos_totales

Interpretación:
  MF < 1 → palas ociosas (flota insuficiente o despachador ineficiente)
  MF = 1 → equilibrio teórico
  MF > 1 → camiones en cola (flota sobredimensionada o mal despachada)
"""


def calcular_match_factor(engine) -> float:
    mine = engine.mine
    duracion_min = engine.env.now
    if duracion_min <= 0:
        return 0.0

    n_trucks = len(mine.camiones)
    total_cycles = sum(c.ciclos_completados for c in mine.camiones.values())
    if total_cycles == 0:
        return 0.0

    # Tiempo promedio de ciclo completo por camión
    T_c = (duracion_min * n_trucks) / total_cycles

    # Tiempo promedio de carga ponderado por número de cargas
    total_loads = sum(p.n_cargas for p in mine.palas.values())
    if total_loads == 0:
        return 0.0
    T_s = sum(p.tiempo_carga_min * p.n_cargas for p in mine.palas.values()) / total_loads

    # Solo contar palas que efectivamente trabajaron
    n_active = sum(1 for p in mine.palas.values() if p.n_cargas > 0)
    if n_active == 0:
        return 0.0

    return (n_trucks * T_s) / (n_active * T_c)
