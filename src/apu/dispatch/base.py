from abc import ABC, abstractmethod


class Dispatcher(ABC):
    """
    Interfaz común para todos los despachadores.

    decide() recibe el estado actual de la mina y el camión que acaba de
    terminar de descargar (y por lo tanto está libre), y retorna la Pala
    a la que debe dirigirse vacío.

    La decisión sobre dónde descargar (chancadora vs botadero) la toma
    el motor de simulación basándose en la ley del material de la pala,
    no el despachador. Esto separa la decisión de flujo de la decisión
    de asignación.
    """

    @abstractmethod
    def decide(self, mine_state, truck) -> "Pala":
        ...

    @property
    def nombre(self) -> str:
        return self.__class__.__name__
