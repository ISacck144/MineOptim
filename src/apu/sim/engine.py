"""
Motor de simulación de eventos discretos basado en SimPy.
Orquesta el ciclo de vida de cada camión y registra todos los eventos
en un log que permite reconstruir la simulación cuadro a cuadro.
"""

import time
import yaml
import simpy

from .mine import EstadoMina
from .truck import Camion, EstadoCamion
from .shovel import Pala
from .dump import Destino, TipoDestino
from .road import RedVial


def cargar_config(ruta_yaml: str) -> dict:
    with open(ruta_yaml, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class MotorSimulacion:
    def __init__(self, config: dict, dispatcher):
        self.config = config
        self.dispatcher = dispatcher
        self.env = simpy.Environment()
        self.mine: EstadoMina = None
        self.log_eventos: list[dict] = []   # tick file: reconstrucción cuadro a cuadro
        self._t_inicio_real: float = None

    # ──────────────────────────────────────────────────────────────────────────
    # Construcción del estado inicial de la mina desde el YAML
    # ──────────────────────────────────────────────────────────────────────────

    def _construir_mina(self):
        cfg = self.config

        palas = [
            Pala(
                id=p['id'],
                ley_cu=p['ley_cu'],
                ley_as=p.get('ley_as', 0.0),
                es_mineral=p['es_mineral'],
                capacidad_ton_h=p['capacidad_ton_h'],
                tiempo_carga_min=p['tiempo_carga_min'],
                pos_x=p.get('pos_x', 0.0),
                pos_y=p.get('pos_y', 0.0),
            )
            for p in cfg['palas']
        ]

        camiones = [
            Camion(
                id=c['id'],
                tipo=c['tipo'],
                capacidad_ton=c['capacidad_ton'],
            )
            for c in cfg['camiones']
        ]

        destinos = [
            Destino(
                id=d['id'],
                tipo=TipoDestino(d['tipo']),
                pos_x=d.get('pos_x', 0.0),
                pos_y=d.get('pos_y', 0.0),
                tiempo_descarga_min=d['tiempo_descarga_min'],
                capacidad_ton_h=d.get('capacidad_ton_h', float('inf')),
            )
            for d in cfg['destinos']
        ]

        red = RedVial(cfg.get('tiempos_viaje_min', {}))
        self.mine = EstadoMina(palas, camiones, destinos, red)

        # Asignar recursos SimPy a cada pala (solo una carga a la vez)
        for pala in self.mine.palas.values():
            pala.resource = simpy.Resource(self.env, capacity=1)

    # ──────────────────────────────────────────────────────────────────────────
    # Proceso SimPy de un camión — se ejecuta concurrentemente con todos los demás
    # ──────────────────────────────────────────────────────────────────────────

    def _ciclo_camion(self, camion: Camion):
        """
        Ciclo de vida del camión:
          (vacío) solicita pala → viaja → espera cola → carga → viaja cargado
          → descarga → (repite desde solicitar pala)

        Este es un generador Python (contiene yield); SimPy lo gestiona como
        un proceso concurrente de eventos discretos.
        """
        # Posición inicial: todos los camiones parten como si acabaran de descargar
        # en la chancadora (punto de referencia para el primer despacho)
        primer_destino = next(
            d for d in self.mine.destinos.values()
            if d.tipo == TipoDestino.CHANCADORA
        )
        camion.pos_actual = primer_destino.id

        while True:
            # ── 1. SOLICITAR ASIGNACIÓN ──────────────────────────────────────
            camion.estado = EstadoCamion.VACIO_EN_RUTA
            pala = self.dispatcher.decide(self.mine, camion)
            camion.shovel_asignada = pala.id

            # ── 2. VIAJAR VACÍO A LA PALA ────────────────────────────────────
            t_viaje_vacio = self.mine.red_vial.tiempo_viaje(camion.pos_actual, pala.id)
            yield self.env.timeout(t_viaje_vacio)
            camion.pos_actual = pala.id
            camion.tiempo_viaje_total_min += t_viaje_vacio

            # ── 3. ESPERAR EN COLA Y CARGAR ──────────────────────────────────
            camion.estado = EstadoCamion.ESPERANDO_CARGA
            t_ini_espera = self.env.now

            with pala.resource.request() as req:
                yield req   # bloquea hasta que la pala quede libre
                t_espera = self.env.now - t_ini_espera
                camion.tiempo_espera_total_min += t_espera

                camion.estado = EstadoCamion.CARGANDO
                yield self.env.timeout(pala.tiempo_carga_min)

                camion.payload_actual = camion.capacidad_ton
                pala.toneladas_cargadas += camion.capacidad_ton
                pala.tiempo_activa_min += pala.tiempo_carga_min
                pala.n_cargas += 1

            self._log('carga', {
                'camion': camion.id, 'pala': pala.id,
                'ton': camion.payload_actual, 'espera_min': t_espera
            })

            # ── 4. DECIDIR DESTINO SEGÚN LA LEY DE LA PALA ──────────────────
            # La ley determina si el material va a chancadora o botadero.
            # Esta lógica se extenderá con la PL de nivel superior en v2.
            destino = self.mine.destino_para_pala(pala)

            # ── 5. VIAJAR CARGADO AL DESTINO ─────────────────────────────────
            camion.estado = EstadoCamion.CARGADO_EN_RUTA
            t_viaje_cargado = self.mine.red_vial.tiempo_viaje(pala.id, destino.id)
            yield self.env.timeout(t_viaje_cargado)
            camion.tiempo_viaje_total_min += t_viaje_cargado

            # ── 6. DESCARGAR ──────────────────────────────────────────────────
            camion.estado = EstadoCamion.DESCARGANDO
            yield self.env.timeout(destino.tiempo_descarga_min)

            payload = camion.payload_actual
            destino.toneladas_recibidas += payload
            # Toneladas de fino: las que realmente tienen valor económico
            if destino.tipo == TipoDestino.CHANCADORA:
                destino.toneladas_fino += payload * pala.ley_cu / 100.0

            camion.toneladas_transportadas += payload
            camion.payload_actual = 0.0
            camion.pos_actual = destino.id
            camion.ciclos_completados += 1

            self._log('descarga', {
                'camion': camion.id, 'destino': destino.id,
                'ton': payload, 'acum': camion.toneladas_transportadas
            })

    def _log(self, tipo: str, datos: dict):
        self.log_eventos.append({'t': self.env.now, 'tipo': tipo, **datos})

    # ──────────────────────────────────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────────────────────────────────

    def correr(self, duracion_horas: float) -> float:
        """Construye la mina, lanza los procesos y corre la simulación.
        Retorna el tiempo de ejecución real en segundos."""
        self._t_inicio_real = time.time()
        self._construir_mina()

        for camion in self.mine.camiones.values():
            self.env.process(self._ciclo_camion(camion))

        self.env.run(until=duracion_horas * 60.0)
        return time.time() - self._t_inicio_real

    def resumen(self) -> dict:
        """Calcula y retorna todos los KPIs al finalizar la simulación."""
        mine = self.mine
        duracion_min = self.env.now

        ton_chancadora = sum(
            d.toneladas_recibidas for d in mine.destinos.values()
            if d.tipo == TipoDestino.CHANCADORA
        )
        ton_fino = sum(
            d.toneladas_fino for d in mine.destinos.values()
            if d.tipo == TipoDestino.CHANCADORA
        )
        ton_botadero = sum(
            d.toneladas_recibidas for d in mine.destinos.values()
            if d.tipo == TipoDestino.BOTADERO
        )

        ciclos_totales = sum(c.ciclos_completados for c in mine.camiones.values())
        t_espera_total = sum(c.tiempo_espera_total_min for c in mine.camiones.values())

        utilizacion_palas = {
            p.id: (p.tiempo_activa_min / duracion_min * 100.0 if duracion_min > 0 else 0.0)
            for p in mine.palas.values()
        }

        return {
            'duracion_sim_min': duracion_min,
            'ton_chancadora': ton_chancadora,
            'ton_fino': ton_fino,
            'ton_botadero': ton_botadero,
            'ton_total': ton_chancadora + ton_botadero,
            'ciclos_totales': ciclos_totales,
            'tiempo_espera_total_min': t_espera_total,
            'promedio_espera_por_ciclo_min': (
                t_espera_total / ciclos_totales if ciclos_totales > 0 else 0.0
            ),
            'utilizacion_palas': utilizacion_palas,
            'n_eventos_log': len(self.log_eventos),
        }
