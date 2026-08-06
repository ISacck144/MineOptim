from .shovel import Pala
from .dump import Destino, TipoDestino
from .road import RedVial


class EstadoMina:
    """
    Estado global de la mina: todas las palas, camiones y destinos.
    El despachador lee este objeto para tomar decisiones.
    El motor de simulación lo actualiza en cada evento.
    """

    def __init__(self, palas: list, camiones: list, destinos: list, red_vial: RedVial):
        self.palas = {p.id: p for p in palas}
        self.camiones = {c.id: c for c in camiones}
        self.destinos = {d.id: d for d in destinos}
        self.red_vial = red_vial

    def palas_operativas(self) -> list[Pala]:
        """Retorna las palas que no están en falla ni fuera de servicio."""
        return [p for p in self.palas.values() if p.operativa]

    def destino_para_pala(self, pala: Pala) -> Destino:
        """
        Regla de negocio: si la pala extrae mineral (ley > ley de corte)
        va a chancadora; si es desmonte, va al botadero.
        La ley de corte está codificada en el campo es_mineral del YAML.
        """
        tipo_buscado = TipoDestino.CHANCADORA if pala.es_mineral else TipoDestino.BOTADERO
        for d in self.destinos.values():
            if d.tipo == tipo_buscado:
                return d
        raise ValueError(
            f"No hay destino de tipo '{tipo_buscado}' definido en el YAML."
        )
