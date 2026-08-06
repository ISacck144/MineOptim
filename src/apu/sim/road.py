class RedVial:
    """
    Para v0: matriz de tiempos de viaje fijos leída desde el YAML.
    En v2 será reemplazada por cálculo físico (rimpull + derateo por altitud).
    La matriz cubre todos los pares origen–destino que usa el ciclo del camión.
    """

    def __init__(self, tiempos: dict):
        # tiempos: {origen_id: {destino_id: minutos_float}}
        self._tiempos = tiempos

    def tiempo_viaje(self, origen_id: str, destino_id: str) -> float:
        if origen_id == destino_id:
            return 0.0
        try:
            return float(self._tiempos[origen_id][destino_id])
        except KeyError:
            raise KeyError(
                f"Tiempo de viaje no definido en el YAML: '{origen_id}' → '{destino_id}'. "
                f"Agrega la entrada en tiempos_viaje_min."
            )
