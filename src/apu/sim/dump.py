from dataclasses import dataclass, field
from enum import Enum


class TipoDestino(str, Enum):
    CHANCADORA = "chancadora"
    BOTADERO = "botadero"
    STOCKPILE = "stockpile"


@dataclass
class Destino:
    id: str
    tipo: TipoDestino
    pos_x: float
    pos_y: float
    tiempo_descarga_min: float
    capacidad_ton_h: float = float('inf')

    toneladas_recibidas: float = 0.0
    # toneladas_fino: solo aplica cuando tipo == CHANCADORA
    toneladas_fino: float = 0.0
