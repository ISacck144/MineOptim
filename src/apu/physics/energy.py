"""
Modelo de consumo de combustible de camiones mineros.

Consumo (L) = distancia_km × consumo_base_L_km × factor_carga × factor_pendiente

  factor_carga     = 1 + (carga_ton / cap_ref_ton) × 0.60
  factor_pendiente = 1 + max(0, pendiente_pct) / 15.0

KPIs derivados:
  eficiencia_L_ton = combustible_total_L / ton_fino_total
  (cuántos litros se queman por tonelada de cobre fino producida)

Fuente metodológica (parámetros son orientativos para la clase de equipo):
  CAT 793F Performance Handbook Ed. 47 — sección "Fuel Consumption".
  Los valores se califican como SINTÉTICOS y deben validarse con datos reales.
"""


def consumo_litros(
    distancia_m: float,
    carga_ton: float,
    pendiente_pct: float,
    config: dict,
) -> float:
    """
    Retorna el combustible consumido en litros para un viaje.

    config debe tener:
        consumo_base_L_km : litros/km en vacío en terreno plano (def. 0.30)
        cap_ref_ton       : capacidad de referencia para el factor de carga (def. 227)
    """
    base   = config.get('consumo_base_L_km', 0.30)
    cap    = config.get('cap_ref_ton', 227)
    dist_km = distancia_m / 1000.0

    f_carga = 1.0 + (carga_ton / cap) * 0.60
    f_pend  = 1.0 + max(0.0, pendiente_pct) / 15.0

    return dist_km * base * f_carga * f_pend


def eficiencia_L_ton(combustible_total_L: float, ton_fino: float) -> float:
    """L de combustible por tonelada de cobre fino producida."""
    if ton_fino <= 0:
        return float('inf')
    return combustible_total_L / ton_fino
