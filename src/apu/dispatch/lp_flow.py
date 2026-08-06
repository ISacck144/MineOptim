"""
Nivel superior del despachador APU: Programación Lineal (PL) con PuLP.

Se resuelve cada 30 minutos simulados para calcular el flujo óptimo
de toneladas/hora desde cada pala a cada destino.

Formulación:
  Variables : x[s] = ton/h de pala mineral s a chancadora
  Objetivo  : max Σ ley_cu[s] · x[s]
  S. a.     :
    x[s]  <= cap_pala[s]                        (capacidad de pala)
    Σ x[s] <= cap_chancadora                    (cuello de botella)
    Σ (ley[s] - L_min) · x[s] >= 0             (ley mínima de mezcla)
    Σ (ley[s] - L_max) · x[s] <= 0             (ley máxima)
    Σ (ley_as[s] - As_max) · x[s] <= 0         (límite de arsénico)
    x[s] >= 0

La solución devuelve un plan {pala_id: ton_h_a_chancadora} que el
HungarianDispatcher (nivel inferior) usa para calcular el término
λ · desviación_del_plan en su función de costo.
"""

try:
    from pulp import (
        LpProblem, LpVariable, LpMaximize, lpSum,
        value, PULP_CBC_CMD, LpStatus,
    )
    _PULP_OK = True
except ImportError:
    _PULP_OK = False

from ..sim.dump import TipoDestino


class LPFlowPlanner:
    """
    Nivel superior de APU.

    resolver() devuelve el plan óptimo y es llamado por el motor
    de simulación cada 30 min simulados (configurable en YAML).
    """

    def __init__(self, config_planta: dict):
        self._ley_min  = config_planta.get('ley_cu_min',  0.40)
        self._ley_max  = config_planta.get('ley_cu_max',  0.90)
        self._as_max   = config_planta.get('ley_as_max',  0.10)
        self._n_iter   = 0

    def resolver(self, mine) -> dict:
        """
        Retorna {pala_id: ton_h_a_chancadora} para las palas operativas.

        Si PuLP no está instalado o el LP es infactible, devuelve un plan
        proporcional a las capacidades de las palas (heurístico de respaldo).
        """
        self._n_iter += 1

        palas_min = [p for p in mine.palas_operativas() if p.es_mineral]
        if not palas_min:
            return {}

        chca = next(
            (d for d in mine.destinos.values() if d.tipo == TipoDestino.CHANCADORA),
            None,
        )
        cap_chca = chca.capacidad_ton_h if chca else float('inf')

        if not _PULP_OK:
            return self._plan_heuristico(palas_min, cap_chca)

        prob = LpProblem(f'apu_flujo_{self._n_iter}', LpMaximize)

        x = {p.id: LpVariable(f'x_{p.id}', lowBound=0, upBound=p.capacidad_ton_h)
             for p in palas_min}

        # Objetivo: maximizar toneladas de fino
        prob += lpSum(p.ley_cu * x[p.id] for p in palas_min)

        # Capacidad de la chancadora
        prob += lpSum(x[p.id] for p in palas_min) <= cap_chca

        # Ley mínima de mezcla (linealizada): Σ (ley - L_min) · x >= 0
        prob += lpSum((p.ley_cu - self._ley_min) * x[p.id] for p in palas_min) >= 0

        # Ley máxima de mezcla
        prob += lpSum((p.ley_cu - self._ley_max) * x[p.id] for p in palas_min) <= 0

        # Límite de arsénico
        prob += lpSum((p.ley_as - self._as_max) * x[p.id] for p in palas_min) <= 0

        prob.solve(PULP_CBC_CMD(msg=0))

        if LpStatus[prob.status] != 'Optimal':
            return self._plan_heuristico(palas_min, cap_chca)

        return {p.id: max(0.0, value(x[p.id]) or 0.0) for p in palas_min}

    # ─────────────────────────────────────────────────────────────────────────

    def _plan_heuristico(self, palas_min: list, cap_chca: float) -> dict:
        """Reparto proporcional a capacidad cuando el LP no está disponible."""
        cap_total = sum(p.capacidad_ton_h for p in palas_min)
        if cap_total <= 0:
            return {}
        factor = min(1.0, cap_chca / cap_total)
        return {p.id: p.capacidad_ton_h * factor for p in palas_min}
