"""
Cálculo de velocidad de camión minero por rimpull.

Modelo simplificado:
  RT  = pendiente (%) + RR × 100          (resistencia total en %)
  F_r = PBV × RT / 100                   (fuerza de rimpull requerida en kN)
  v   = min(v_max, P_ef / F_r × 3.6)     (km/h, limitado por motor o rampa)

Referencia de dominio:
  Caterpillar Performance Handbook Ed. 47, sección "Rimpull".
  Los coeficientes son representativos de equipos de 200–300 t.
"""

from .altitude import factor_derateo


def calcular_velocidad_kmh(
    carga_ton: float,
    pendiente_pct: float,
    altitud_msnm: float,
    config_vehiculo: dict,
    config_fisica: dict,
) -> float:
    """Velocidad en km/h para un camión sobre un tramo dado."""
    peso_bruto_ton = config_vehiculo.get('peso_vacio_ton', 140) + carga_ton
    potencia_kw    = config_vehiculo.get('potencia_kw', 2600)
    v_max          = config_vehiculo.get('v_max_kmh', 45.0)

    rr_pct  = config_fisica.get('coef_rodadura', 0.025) * 100
    rt_pct  = pendiente_pct + rr_pct

    f_alt   = factor_derateo(altitud_msnm, config_fisica)
    p_ef_kw = potencia_kw * f_alt

    peso_kn  = peso_bruto_ton * 9.81
    f_req_kn = peso_kn * rt_pct / 100.0

    if f_req_kn <= 0:
        return v_max
    v_por_potencia = (p_ef_kw / f_req_kn) * 3.6
    return min(v_max, max(3.0, v_por_potencia))


def calcular_tiempo_min(
    distancia_m: float,
    carga_ton: float,
    pendiente_pct: float,
    altitud_msnm: float,
    config_vehiculo: dict,
    config_fisica: dict,
) -> float:
    """Retorna el tiempo de viaje en minutos para el tramo dado."""
    v_kmh = calcular_velocidad_kmh(
        carga_ton, pendiente_pct, altitud_msnm, config_vehiculo, config_fisica
    )
    return (distancia_m / 1000.0) / v_kmh * 60.0
