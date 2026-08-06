from dataclasses import dataclass, field
from enum import Enum


class EstadoCamion(str, Enum):
    ESPERANDO_CARGA = "esperando_carga"
    CARGANDO = "cargando"
    CARGADO_EN_RUTA = "cargado_en_ruta"
    ESPERANDO_DESCARGA = "esperando_descarga"
    DESCARGANDO = "descargando"
    VACIO_EN_RUTA = "vacio_en_ruta"
    FUERA_DE_SERVICIO = "fuera_de_servicio"


@dataclass
class Camion:
    id: str
    tipo: str
    capacidad_ton: float

    estado: EstadoCamion = EstadoCamion.VACIO_EN_RUTA
    payload_actual: float = 0.0
    pos_actual: str = ""          # id del nodo donde está (pala o destino)
    shovel_asignada: str = ""     # id de la pala hacia la que va

    # Acumuladores para cálculo de KPIs al final de la simulación
    toneladas_transportadas: float = 0.0
    tiempo_espera_total_min: float = 0.0
    tiempo_viaje_total_min: float = 0.0
    ciclos_completados: int = 0

    # Estado de falla (v2)
    en_falla: bool = False
