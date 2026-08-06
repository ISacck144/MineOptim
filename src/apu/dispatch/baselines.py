"""
Los 5 despachadores de referencia de la literatura (Alarie & Gamache, 2002).
Son los baselines contra los que APU compite.
Implementarlos es lo que da credibilidad: no son reglas inventadas.
"""

import random
from .base import Dispatcher


class ShortestQueue(Dispatcher):
    """
    Baseline más común: la pala con la cola más corta.
    Miope: ignora el tiempo de viaje y el plan global.
    """

    def __init__(self):
        super().__init__()

    def _decide(self, mine_state, truck):
        palas = mine_state.palas_operativas()
        return min(palas, key=lambda p: p.resource.count + len(p.resource.queue))


class Random(Dispatcher):
    """
    Límite inferior teórico: asignación completamente aleatoria.
    Útil para establecer la escala de mejora de los demás métodos.
    """

    def __init__(self, seed: int = None):
        super().__init__()
        self._rng = random.Random(seed)

    def _decide(self, mine_state, truck):
        return self._rng.choice(mine_state.palas_operativas())


class Nearest(Dispatcher):
    """
    Menor tiempo de viaje desde la posición actual del camión.
    Minimiza el acarreo vacío, pero ignora colas y tipo de material.
    Puede quedar atrapado en ciclos pala_desmonte ↔ botadero.
    """

    def __init__(self):
        super().__init__()

    def _decide(self, mine_state, truck):
        palas = mine_state.palas_operativas()
        return min(
            palas,
            key=lambda p: mine_state.red_vial.tiempo_viaje(truck.pos_actual, p.id)
        )


class SPTF(Dispatcher):
    """
    Shortest Processing Time First: la pala con menor tiempo de carga.
    Análogo al algoritmo SJF en scheduling de SO.
    Maximiza throughput de carga si los tiempos de viaje son iguales,
    pero genera colas severas cuando todos convergen a la misma pala.
    """

    def __init__(self):
        super().__init__()

    def _decide(self, mine_state, truck):
        palas = mine_state.palas_operativas()
        return min(palas, key=lambda p: p.tiempo_carga_min)


class FixedGroup(Dispatcher):
    """
    Camiones atados permanentemente a palas.
    Es el método que se usa en operaciones con múltiples contratistas
    (cada contratista maneja sus propios camiones y su propia pala).
    Máxima simplicidad operativa, mínima adaptabilidad a eventos.
    """

    def __init__(self, asignaciones: dict):
        super().__init__()
        # asignaciones: {truck_id: shovel_id}
        self._asignaciones = asignaciones

    def _decide(self, mine_state, truck):
        shovel_id = self._asignaciones.get(truck.id)
        if shovel_id and shovel_id in mine_state.palas:
            pala = mine_state.palas[shovel_id]
            if pala in mine_state.palas_operativas():
                return pala
        # Fallback cuando la pala asignada falla (activo desde v2)
        palas = mine_state.palas_operativas()
        return min(palas, key=lambda p: p.resource.count + len(p.resource.queue))
