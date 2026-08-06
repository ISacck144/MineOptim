"""
Los 5 despachadores de referencia de la literatura (Alarie & Gamache, 2002).
Son los baselines contra los que APU compite.
Implementarlos es lo que da credibilidad: no son reglas inventadas.
"""

import random
from .base import Dispatcher


class ShortestQueue(Dispatcher):
    """
    Baseline más común: asigna el camión a la pala con la cola más corta
    (menor número de camiones esperando o cargando).
    Miope: no considera el tiempo de viaje ni el plan global.
    """

    def decide(self, mine_state, truck):
        palas = mine_state.palas_operativas()
        # resource.count = camiones cargando ahora; resource.queue = esperando
        return min(palas, key=lambda p: p.resource.count + len(p.resource.queue))


class Random(Dispatcher):
    """
    Límite inferior teórico: asignación completamente aleatoria.
    Útil para establecer la escala de mejora de los otros métodos.
    """

    def __init__(self, seed: int = None):
        self._rng = random.Random(seed)

    def decide(self, mine_state, truck):
        return self._rng.choice(mine_state.palas_operativas())


class Nearest(Dispatcher):
    """
    Asigna a la pala más cercana (menor tiempo de viaje desde posición actual).
    Minimiza el tiempo de acarreo vacío, pero ignora las colas.
    """

    def decide(self, mine_state, truck):
        palas = mine_state.palas_operativas()
        return min(
            palas,
            key=lambda p: mine_state.red_vial.tiempo_viaje(truck.pos_actual, p.id)
        )


class SPTF(Dispatcher):
    """
    Shortest Processing Time First: asigna a la pala con menor tiempo de carga.
    Análogo al algoritmo SJF (Shortest Job First) en scheduling de SO.
    Maximiza el throughput si los tiempos de viaje son iguales,
    pero ignora las colas y las distancias.
    """

    def decide(self, mine_state, truck):
        palas = mine_state.palas_operativas()
        return min(palas, key=lambda p: p.tiempo_carga_min)


class FixedGroup(Dispatcher):
    """
    Despacho por grupo fijo: cada camión está atado permanentemente a una pala.
    Es el método que realmente se usa en operaciones con múltiples contratistas
    (cada contratista maneja su propio grupo de camiones y su propia pala).
    Máxima simplicidad operativa, mínima eficiencia global.
    """

    def __init__(self, asignaciones: dict):
        # asignaciones: {truck_id: shovel_id}
        self._asignaciones = asignaciones

    def decide(self, mine_state, truck):
        shovel_id = self._asignaciones.get(truck.id)
        if shovel_id and shovel_id in mine_state.palas:
            pala = mine_state.palas[shovel_id]
            # Si la pala asignada está operativa, ir a ella
            if pala in mine_state.palas_operativas():
                return pala
        # Fallback: ShortestQueue (cuando la pala asignada falla — v2)
        palas = mine_state.palas_operativas()
        return min(palas, key=lambda p: p.resource.count + len(p.resource.queue))
