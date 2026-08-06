"""
Motor de simulación de eventos discretos basado en SimPy.
Orquesta el ciclo de vida de cada camión y registra todos los eventos
en un log que permite reconstruir la simulación cuadro a cuadro.

v2: añade soporte para eventos aleatorios (GestorEventos), programación
lineal de nivel superior (LPFlowPlanner), ruido estocástico en tiempos
de viaje, y snapshots periódicos para el gráfico de serie temporal.
"""

import time
import yaml
import simpy
import numpy as np

from .mine import EstadoMina
from .truck import Camion, EstadoCamion
from .shovel import Pala
from .dump import Destino, TipoDestino
from .road import RedVial, RedVialDijkstra, TIEMPO_INACCESIBLE


def cargar_config(ruta_yaml: str) -> dict:
    with open(ruta_yaml, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class MotorSimulacion:
    def __init__(self, config: dict, dispatcher):
        self.config     = config
        self.dispatcher = dispatcher
        self.env        = simpy.Environment()
        self.mine: EstadoMina = None
        self.log_eventos: list[dict] = []

        # v2: opcionales
        self.snapshots: list[dict] = []       # [{t_min, ton_fino}]
        self._rng: np.random.Generator = None
        self._v2_cfg: dict = None
        self._gestor_ev = None
        self._lp_planner = None
        self._ml_model = None
        self._flujo_palas: dict[str, float] = {}   # ton acumulado por pala en el intervalo LP
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

        # v3: usar Dijkstra si hay definición de grafo; si no, tabla plana
        if 'red_vial_v3' in cfg:
            red = RedVialDijkstra(cfg['red_vial_v3'])
        else:
            red = RedVial(cfg.get('tiempos_viaje_min', {}))
        self.mine = EstadoMina(palas, camiones, destinos, red)

        # Mapa de coordenadas para el dashboard (node_id → (x, y))
        self._coord_map: dict[str, tuple[float, float]] = {}
        for p in palas:
            self._coord_map[p.id] = (p.pos_x, p.pos_y)
        for d in destinos:
            self._coord_map[d.id] = (d.pos_x, d.pos_y)
        if isinstance(red, RedVialDijkstra):
            for nid, n in red.nodos.items():
                self._coord_map.setdefault(nid, (n.get('pos_x', 0), n.get('pos_y', 0)))

        for pala in self.mine.palas.values():
            pala.resource = simpy.Resource(self.env, capacity=1)

    # ──────────────────────────────────────────────────────────────────────────
    # Ciclo de camión
    # ──────────────────────────────────────────────────────────────────────────

    def _ciclo_camion(self, camion: Camion):
        primer_destino = next(
            d for d in self.mine.destinos.values()
            if d.tipo == TipoDestino.CHANCADORA
        )
        camion.pos_actual = primer_destino.id

        while True:
            # Si el camión está en falla, esperar hasta que sea reparado
            if camion.en_falla:
                camion.estado = EstadoCamion.FUERA_DE_SERVICIO
                yield self.env.timeout(1.0)
                continue

            # ── 1. SOLICITAR ASIGNACIÓN ──────────────────────────────────────
            palas_ok = self.mine.palas_operativas()
            if not palas_ok:
                # Todas las palas fallaron: esperar 1 min y reintentar
                yield self.env.timeout(1.0)
                continue

            camion.estado = EstadoCamion.VACIO_EN_RUTA
            pala = self.dispatcher.decide(self.mine, camion)
            camion.shovel_asignada = pala.id

            # ── 2. VIAJAR VACÍO A LA PALA ────────────────────────────────────
            t_base_vacio = self.mine.red_vial.tiempo_viaje(camion.pos_actual, pala.id)

            # v3: si la ruta está bloqueada, esperar y re-despachar
            if t_base_vacio >= TIEMPO_INACCESIBLE:
                yield self.env.timeout(5.0)  # esperar 5 min y reintentar
                continue

            t_viaje_vacio = self._aplicar_ruido(t_base_vacio)
            yield self.env.timeout(t_viaje_vacio)
            camion.pos_actual = pala.id
            camion.tiempo_viaje_total_min += t_viaje_vacio

            # Registrar residuo ML (viaje vacío)
            if self._ml_model is not None:
                self._registrar_residuo(
                    f'{camion.shovel_asignada}_vacío', t_base_vacio, t_viaje_vacio
                )

            # ── 3. VERIFICAR PALA DESPUÉS DEL VIAJE (puede haber fallado) ───
            if not pala.operativa:
                # Re-despachar sin cargar
                continue

            # ── 4. ESPERAR EN COLA Y CARGAR ──────────────────────────────────
            camion.estado = EstadoCamion.ESPERANDO_CARGA
            t_ini_espera = self.env.now

            cargado = False
            with pala.resource.request() as req:
                yield req
                t_espera = self.env.now - t_ini_espera
                camion.tiempo_espera_total_min += t_espera

                if pala.operativa:   # verificar de nuevo: pudo fallar en cola
                    camion.estado = EstadoCamion.CARGANDO
                    yield self.env.timeout(pala.tiempo_carga_min)

                    camion.payload_actual = camion.capacidad_ton
                    pala.toneladas_cargadas += camion.capacidad_ton
                    pala.tiempo_activa_min  += pala.tiempo_carga_min
                    pala.n_cargas           += 1
                    cargado = True

                    # Acumular flujo real para LP
                    self._flujo_palas[pala.id] = (
                        self._flujo_palas.get(pala.id, 0.0) + camion.capacidad_ton
                    )
                    # Notificar al despachador para el acoplamiento λ
                    if hasattr(self.dispatcher, 'registrar_carga'):
                        self.dispatcher.registrar_carga(pala.id, camion.capacidad_ton)

            if not cargado:
                continue

            self._log('carga', {
                'camion': camion.id, 'pala': pala.id,
                'ton': camion.payload_actual, 'espera_min': t_espera
            })

            # ── 5. DECIDIR DESTINO ────────────────────────────────────────────
            destino = self.mine.destino_para_pala(pala)

            # ── 6. VIAJAR CARGADO ─────────────────────────────────────────────
            camion.estado = EstadoCamion.CARGADO_EN_RUTA
            t_base_cargado = self.mine.red_vial.tiempo_viaje(pala.id, destino.id)
            t_viaje_cargado = self._aplicar_ruido(t_base_cargado)
            yield self.env.timeout(t_viaje_cargado)
            camion.tiempo_viaje_total_min += t_viaje_cargado

            # v3: registrar combustible
            self._registrar_combustible(camion, t_base_vacio, t_viaje_cargado, pala)

            if self._ml_model is not None:
                self._registrar_residuo(
                    f'{pala.id}_{destino.id}', t_base_cargado, t_viaje_cargado
                )

            # ── 7. DESCARGAR ──────────────────────────────────────────────────
            camion.estado = EstadoCamion.DESCARGANDO
            yield self.env.timeout(destino.tiempo_descarga_min)

            payload = camion.payload_actual
            destino.toneladas_recibidas += payload
            if destino.tipo == TipoDestino.CHANCADORA:
                destino.toneladas_fino += payload * pala.ley_cu / 100.0

            camion.toneladas_transportadas += payload
            camion.payload_actual  = 0.0
            camion.pos_actual      = destino.id
            camion.ciclos_completados += 1

            self._log('descarga', {
                'camion': camion.id, 'destino': destino.id,
                'ton': payload, 'acum': camion.toneladas_transportadas
            })

    # ──────────────────────────────────────────────────────────────────────────
    # Procesos periódicos (v2)
    # ──────────────────────────────────────────────────────────────────────────

    def _proceso_snapshots(self, intervalo_min: float = 10.0):
        """Registra ton_fino acumulado cada intervalo_min para la gráfica temporal."""
        while True:
            yield self.env.timeout(intervalo_min)
            ton_fino = sum(
                d.toneladas_fino for d in self.mine.destinos.values()
            )
            self.snapshots.append({'t_min': self.env.now, 'ton_fino': ton_fino})

    def _proceso_lp(self, intervalo_min: float = 30.0):
        """Resuelve la PL y actualiza el plan del despachador cada intervalo."""
        if self._lp_planner is None:
            return
        while True:
            yield self.env.timeout(intervalo_min)
            flujo_actual = {
                pid: ton / (intervalo_min / 60.0)
                for pid, ton in self._flujo_palas.items()
            }
            plan = self._lp_planner.resolver(self.mine)
            if hasattr(self.dispatcher, 'actualizar_plan'):
                self.dispatcher.actualizar_plan(plan, flujo_actual)
            self._flujo_palas.clear()
            self._log('lp_solve', {'plan': {k: round(v, 1) for k, v in plan.items()}})

    def _proceso_ml_fit(self, burn_in_min: float = 120.0):
        """Entrena el modelo ML una vez cumplido el período de burn-in."""
        if self._ml_model is None:
            return
        yield self.env.timeout(burn_in_min)
        exito = self._ml_model.fit()
        self._log('ml_fit', {'exito': exito, 'n_muestras': len(self._ml_model._datos)})

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers internos
    # ──────────────────────────────────────────────────────────────────────────

    def _aplicar_ruido(self, t_base: float) -> float:
        """Añade ruido gaussiano al tiempo de viaje si v2 está activo."""
        if self._rng is None or self._v2_cfg is None:
            return t_base
        sigma = self._v2_cfg.get('fisica', {}).get('ruido_viaje_sigma', 0.0)
        if sigma <= 0.0:
            return t_base
        factor = float(self._rng.normal(1.0, sigma))
        factor = max(0.5, min(2.0, factor))
        return t_base * factor

    def _registrar_combustible(self, camion, t_vacio_min: float,
                               t_cargado_min: float, pala):
        """Acumula consumo de combustible (v3). Usa un modelo simplificado."""
        cfg_e = (self._v2_cfg or {}).get('energia', {})
        if not cfg_e.get('activado', False):
            return
        from ..physics.energy import consumo_litros
        # Distancia estimada a partir del tiempo y velocidad de referencia
        v_ref_kmh = cfg_e.get('velocidad_ref_kmh', 25.0)
        dist_vacio_m   = (t_vacio_min  / 60) * v_ref_kmh * 1000
        dist_cargado_m = (t_cargado_min / 60) * v_ref_kmh * 1000
        pend = cfg_e.get('pendiente_ref_pct', 8.0)
        camion.combustible_litros += consumo_litros(dist_vacio_m, 0, pend, cfg_e)
        camion.combustible_litros += consumo_litros(dist_cargado_m, camion.capacidad_ton,
                                                     -pend, cfg_e)

    def _registrar_residuo(self, tramo_id: str, t_fisica: float, t_real: float):
        """Pasa los residuos al modelo ML si está activo."""
        if self._ml_model is None:
            return
        from ..ml.features import extraer
        n_activos = sum(1 for c in self.mine.camiones.values()
                        if c.estado == EstadoCamion.VACIO_EN_RUTA
                        or c.estado == EstadoCamion.CARGADO_EN_RUTA)
        feats = extraer(self.env.now, tramo_id, n_activos, len(self.mine.camiones))
        self._ml_model.registrar(tramo_id, t_fisica, t_real, feats, self.env.now)

    def _log(self, tipo: str, datos: dict):
        self.log_eventos.append({'t': self.env.now, 'tipo': tipo, **datos})

    # ──────────────────────────────────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────────────────────────────────

    def correr(self, duracion_horas: float,
               v2_config: dict = None,
               gestor_eventos=None,
               lp_planner=None,
               ml_model=None,
               seed: int = 42) -> float:
        """
        Construye la mina, lanza los procesos y corre la simulación.
        Retorna el tiempo de ejecución real en segundos.

        v2_config    : sección 'v2' del YAML (o None para modo v0/v1)
        gestor_eventos: instancia de GestorEventos (opcional)
        lp_planner   : instancia de LPFlowPlanner (opcional)
        ml_model     : instancia de ResidualForestModel (opcional)
        """
        self._t_inicio_real = time.time()
        self._v2_cfg = v2_config
        self._gestor_ev = gestor_eventos
        self._lp_planner = lp_planner
        self._ml_model = ml_model

        if v2_config is not None:
            self._rng = np.random.default_rng(seed)

        self._construir_mina()

        # Procesos de camiones
        for camion in self.mine.camiones.values():
            self.env.process(self._ciclo_camion(camion))

        # Eventos (v2)
        if gestor_eventos is not None:
            gestor_eventos.iniciar(self.env, self.mine, self.log_eventos)

        # LP periódico (v2)
        if lp_planner is not None:
            intervalo_lp = (v2_config or {}).get('despacho', {}).get('intervalo_pl_min', 30.0)
            self.env.process(self._proceso_lp(intervalo_lp))

        # Entrenamiento ML con burn-in (v2)
        if ml_model is not None:
            burn_in = (v2_config or {}).get('ml', {}).get('burn_in_min', 120.0)
            self.env.process(self._proceso_ml_fit(burn_in))

        # Snapshots periódicos (v2)
        if v2_config is not None:
            snap_int = (v2_config or {}).get('snapshot_intervalo_min', 10.0)
            self.env.process(self._proceso_snapshots(snap_int))

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

        # Palas que fallaron al menos una vez
        n_fallas = sum(1 for p in mine.palas.values() if p.tiempo_fuera_servicio_min > 0)

        # v3: energía
        combustible_total = sum(c.combustible_litros for c in mine.camiones.values())
        from ..physics.energy import eficiencia_L_ton
        eficiencia = eficiencia_L_ton(combustible_total, ton_fino)

        return {
            'duracion_sim_min'          : duracion_min,
            'ton_chancadora'            : ton_chancadora,
            'ton_fino'                  : ton_fino,
            'ton_botadero'              : ton_botadero,
            'ton_total'                 : ton_chancadora + ton_botadero,
            'ciclos_totales'            : ciclos_totales,
            'tiempo_espera_total_min'   : t_espera_total,
            'promedio_espera_por_ciclo_min': (
                t_espera_total / ciclos_totales if ciclos_totales > 0 else 0.0
            ),
            'utilizacion_palas'         : utilizacion_palas,
            'n_eventos_log'             : len(self.log_eventos),
            'n_fallas_palas'            : n_fallas,
            'combustible_total_L'       : combustible_total,
            'eficiencia_L_ton'          : eficiencia,
        }
