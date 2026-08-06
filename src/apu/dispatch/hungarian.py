"""
Nivel inferior del despachador APU: asignación individual resuelta con
el método húngaro (Kuhn-Munkres, O(n³)).

Función de costo (v2):
  c_j = t_viaje(i→j)
       + t_cola_estimada(j)
       + bias_ley(j)
       - λ · desviacion_plan(j)

El término λ · desviación_plan acopla los dos niveles:
  desviacion_plan(j) = max(0, plan_ton_h[j] - actual_ton_h[j])

Cuando la PL dice que la pala j debe producir más de lo que está
produciendo, el costo de ir a j disminuye → el Húngaro dirige más
camiones allí → la producción sube hasta alcanzar el plan.
"""

import numpy as np
from scipy.optimize import linear_sum_assignment
from .base import Dispatcher


class HungarianDispatcher(Dispatcher):
    """
    Despachador APU nivel inferior.

    En v1 opera con heurístico de ley; en v2 recibe el plan de la PL
    mediante actualizar_plan() que el motor llama cada 30 min simulados.
    """

    def __init__(self, penalizacion_desmonte: float = 60.0,
                 peso_ley: float = 50.0, lambda_acoplamiento: float = 0.5):
        super().__init__()
        self._pen_desmonte = penalizacion_desmonte
        self._peso_ley     = peso_ley
        self._lambda       = lambda_acoplamiento

        # Plan LP: {pala_id: ton_h_deseado}
        self._plan: dict[str, float] = {}
        # Flujo real en el intervalo actual: {pala_id: ton_h}
        self._flujo_real: dict[str, float] = {}

    # ─────────────────────────────────────────────────────────────────────────
    # Acoplamiento con nivel superior (LP)
    # ─────────────────────────────────────────────────────────────────────────

    def actualizar_plan(self, plan: dict, flujo_real: dict = None):
        """
        Llamado por el motor cada intervalo_pl_min minutos.

        plan       : {pala_id: ton_h_a_chancadora}  ← salida del LP
        flujo_real : {pala_id: ton_h_real}           ← medido en el intervalo
        """
        self._plan = plan or {}
        self._flujo_real = flujo_real or {}

    def registrar_carga(self, pala_id: str, ton: float):
        """El motor llama esto en cada evento de carga para acumular flujo real."""
        self._flujo_real[pala_id] = self._flujo_real.get(pala_id, 0.0) + ton

    # ─────────────────────────────────────────────────────────────────────────
    # Decisión de despacho
    # ─────────────────────────────────────────────────────────────────────────

    def _decide(self, mine_state, truck):
        palas = mine_state.palas_operativas()
        if not palas:
            # Sin palas operativas: no debería ocurrir, pero si pasa, retorna
            # la primera pala disponible (fallback absoluto)
            return next(iter(mine_state.palas.values()))

        n = len(palas)
        costos = np.empty((1, n))

        for j, pala in enumerate(palas):
            t_viaje  = mine_state.red_vial.tiempo_viaje(truck.pos_actual, pala.id)
            n_cola   = pala.resource.count + len(pala.resource.queue)
            t_cola   = n_cola * pala.tiempo_carga_min

            bias_ley = (
                (1.0 - pala.ley_cu) * self._peso_ley
                if pala.es_mineral
                else self._pen_desmonte
            )

            # Término de acoplamiento LP ↔ Húngaro
            # desviacion RELATIVA (0..1) para que sea comparable con t_viaje [min]
            plan_th = self._plan.get(pala.id, 0.0)
            real_th = self._flujo_real.get(pala.id, 0.0) * 2.0   # ton → ton/h (30-min window)
            if plan_th > 0:
                desviacion_rel = max(0.0, min(1.0, (plan_th - real_th) / plan_th))
            else:
                desviacion_rel = 0.0
            # Bonus máximo acotado a 20 min (mismo orden que t_viaje)
            bonus = self._lambda * 20.0 * desviacion_rel

            costos[0, j] = t_viaje + t_cola + bias_ley - bonus

        _, col_ind = linear_sum_assignment(costos)
        return palas[col_ind[0]]

    @property
    def nombre(self) -> str:
        return "APU_Hungaro"
