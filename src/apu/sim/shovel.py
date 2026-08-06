from dataclasses import dataclass, field


@dataclass
class Pala:
    id: str
    ley_cu: float            # % de cobre en el material extraído
    ley_as: float            # % de arsénico (restricción de mezcla en v2)
    es_mineral: bool         # True → va a chancadora; False → va a botadero
    capacidad_ton_h: float   # toneladas/hora teórica de la pala
    tiempo_carga_min: float  # minutos por ciclo de carga (un camión)
    pos_x: float = 0.0
    pos_y: float = 0.0

    # Acumuladores de métricas
    toneladas_cargadas: float = 0.0
    tiempo_activa_min: float = 0.0   # minutos con camión cargando
    n_cargas: int = 0

    # Recurso SimPy; se asigna desde el engine para evitar dependencia circular
    resource: object = field(default=None, repr=False)
