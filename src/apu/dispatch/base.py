import time
from abc import ABC, abstractmethod


class Dispatcher(ABC):
    """
    Interfaz común para todos los despachadores.

    decide() envuelve _decide() con cronometraje automático.
    Las subclases implementan _decide(), no decide().
    Esto permite medir la ADL (Algorithm Decision Latency) sin
    repetir código de temporización en cada implementación.
    """

    def __init__(self):
        self._adl_tiempos_s: list[float] = []

    def decide(self, mine_state, truck) -> "Pala":
        t0 = time.perf_counter()
        resultado = self._decide(mine_state, truck)
        self._adl_tiempos_s.append(time.perf_counter() - t0)
        return resultado

    @abstractmethod
    def _decide(self, mine_state, truck) -> "Pala":
        ...

    def adl_promedio_ms(self) -> float:
        """Latencia promedio de decisión en milisegundos."""
        if not self._adl_tiempos_s:
            return 0.0
        return sum(self._adl_tiempos_s) / len(self._adl_tiempos_s) * 1000.0

    @property
    def nombre(self) -> str:
        return self.__class__.__name__
