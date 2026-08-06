"""
Nivel inferior del despachador APU: problema de asignación individual
resuelto con el método húngaro (Kuhn-Munkres, O(n³)).

Función de costo para asignar el camión i a la pala j:
  c_j = t_viaje(i→j) + t_cola_estimada(j) + bias_desmonte

El término bias_desmonte evita enviar camiones a palas de desmonte
cuando hay palas minerales disponibles. En v2, este heurístico es
reemplazado por el término λ·desviación_del_plan proveniente de la PL.
"""

import numpy as np
from scipy.optimize import linear_sum_assignment
from .base import Dispatcher


class HungarianDispatcher(Dispatcher):
    """
    Despachador APU nivel inferior.

    A diferencia de los baselines que optimizan UNA sola variable
    (solo cola o solo distancia), este despachador minimiza el costo
    combinado: tiempo de viaje + tiempo de espera estimado en cola.

    Usa scipy.optimize.linear_sum_assignment para mantener la estructura
    del código lista para v2, donde la función de costo incluirá el
    término de desviación del plan LP (nivel superior).
    """

    def __init__(self, penalizacion_desmonte: float = 60.0, peso_ley: float = 50.0):
        super().__init__()
        # Penalización en minutos para palas de desmonte.
        self._pen_desmonte = penalizacion_desmonte
        # Sin plan LP, usamos el peso_ley como proxy de valor:
        # palas con menor ley_cu reciben mayor costo (se prefieren las de alta ley).
        # El LP de v2 reemplaza este heurístico con el término λ·desviación_plan.
        self._peso_ley = peso_ley

    def _decide(self, mine_state, truck):
        palas = mine_state.palas_operativas()
        n = len(palas)

        costos = np.empty((1, n))
        for j, pala in enumerate(palas):
            t_viaje = mine_state.red_vial.tiempo_viaje(truck.pos_actual, pala.id)

            # Tiempo de espera ponderado por t_carga (más fino que solo contar cola)
            n_en_cola = pala.resource.count + len(pala.resource.queue)
            t_cola = n_en_cola * pala.tiempo_carga_min

            # Costo de baja ley: prefiere palas con más cobre.
            # (1 - ley_cu) × peso_ley → pala con ley 0.85: 7.5; con ley 0.55: 22.5
            bias_ley = (1.0 - pala.ley_cu) * self._peso_ley if pala.es_mineral else self._pen_desmonte

            costos[0, j] = t_viaje + t_cola + bias_ley

        # Para un camión único, linear_sum_assignment retorna el argmin.
        # La estructura de matriz 1×n prepara el acoplamiento con v2,
        # donde serán múltiples camiones asignados simultáneamente.
        _, col_ind = linear_sum_assignment(costos)
        return palas[col_ind[0]]

    @property
    def nombre(self) -> str:
        return "APU_Hungaro"
