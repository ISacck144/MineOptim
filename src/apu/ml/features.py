"""
Ingeniería de features para el predictor de residuo physics-informed.

Features del residuo (t_real - t_fisica) por tramo:
  - hora_fraccion  : hora del día normalizada (0–1)
  - es_guardia     : 0 = mañana, 1 = tarde, 2 = noche
  - tramo_enc      : hash del tramo_id mod 16 (encoding compacto)
  - congestion     : estimación de ocupación de la vía (0–1)
"""

import math


def extraer(t_min: float, tramo_id: str, n_camiones_activos: int,
            n_camiones_total: int) -> list[float]:
    """
    Retorna un vector de features [hora_frac, guardia, tramo_enc, congestion].

    t_min              : tiempo simulado actual en minutos
    tramo_id           : cadena "origen_destino"
    n_camiones_activos : camiones viajando en este instante
    n_camiones_total   : flota total
    """
    hora_frac = (t_min % (24 * 60)) / (24 * 60)   # 0..1 dentro del día
    turno_num = int((t_min % (24 * 60)) / 480) % 3  # 0/1/2 (turnos 8 h)
    tramo_enc = hash(tramo_id) % 16 / 15.0          # 0..1
    congestion = n_camiones_activos / max(1, n_camiones_total)
    return [hora_frac, float(turno_num) / 2.0, tramo_enc, congestion]
