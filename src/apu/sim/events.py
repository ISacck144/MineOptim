"""
Gestión de eventos aleatorios y programados de la mina.

Fallas de pala  → MTBF exponencial, reparación normal
Fallas de camión → misma distribución
Evento programado → para la demo: "romper pala_2 en minuto 300"

El GestorEventos lanza procesos SimPy que modifican el flag `operativa`
de cada pala. El motor de simulación chequea ese flag en cada ciclo de
camión, lo que fuerza a los despachadores a adaptarse inmediatamente.
"""

import numpy as np


class GestorEventos:
    def __init__(self, config_v2: dict, rng: np.random.Generator = None):
        self._cfg = config_v2
        self._rng = rng or np.random.default_rng(99)
        self.log: list[dict] = []
        self._env = None
        self._mine = None
        self._log_global = None

    # ─────────────────────────────────────────────────────────────────────────
    # API pública
    # ─────────────────────────────────────────────────────────────────────────

    def iniciar(self, env, mine, log_global: list):
        self._env = env
        self._mine = mine
        self._log_global = log_global

        cfg_ev = self._cfg.get('eventos', {})

        for ev in cfg_ev.get('programados', []):
            tipo = ev.get('tipo')
            if tipo == 'falla_pala':
                env.process(self._falla_pala_programada(
                    ev['pala_id'], ev['tiempo_min'], ev['duracion_min']
                ))
            elif tipo == 'falla_camion':
                env.process(self._falla_camion_programada(
                    ev['camion_id'], ev['tiempo_min'], ev['duracion_min']
                ))
            elif tipo == 'bloqueo_via':
                env.process(self._bloqueo_via_programado(
                    ev['from'], ev['to'], ev['tiempo_min'], ev['duracion_min']
                ))

        cfg_al = cfg_ev.get('aleatorios', {})
        if cfg_al.get('activado', False):
            for pala_id in mine.palas:
                env.process(self._fallas_aleatorias_pala(pala_id, cfg_al))

    # ─────────────────────────────────────────────────────────────────────────
    # Procesos SimPy — eventos programados
    # ─────────────────────────────────────────────────────────────────────────

    def _falla_pala_programada(self, pala_id: str, tiempo_min: float, duracion_min: float):
        yield self._env.timeout(tiempo_min)
        pala = self._mine.palas.get(pala_id)
        if pala is None or not pala.operativa:
            return
        pala.operativa = False
        self._reg('falla_pala_programada', pala=pala_id, duracion=duracion_min)
        yield self._env.timeout(duracion_min)
        pala.operativa = True
        pala.tiempo_fuera_servicio_min += duracion_min
        self._reg('recuperacion_pala', pala=pala_id)

    def _falla_camion_programada(self, camion_id: str, tiempo_min: float, duracion_min: float):
        yield self._env.timeout(tiempo_min)
        camion = self._mine.camiones.get(camion_id)
        if camion is None:
            return
        camion.en_falla = True
        self._reg('falla_camion_programada', camion=camion_id, duracion=duracion_min)
        yield self._env.timeout(duracion_min)
        camion.en_falla = False
        self._reg('recuperacion_camion', camion=camion_id)

    # ─────────────────────────────────────────────────────────────────────────
    # Procesos SimPy — eventos aleatorios
    # ─────────────────────────────────────────────────────────────────────────

    def _fallas_aleatorias_pala(self, pala_id: str, cfg: dict):
        mtbf      = cfg.get('mtbf_pala_min', 480.0)
        mtr_mu    = cfg.get('mtr_pala_min',   45.0)
        mtr_std   = cfg.get('mtr_pala_std',   10.0)

        while True:
            t_hasta = float(self._rng.exponential(mtbf))
            yield self._env.timeout(t_hasta)

            pala = self._mine.palas.get(pala_id)
            if pala is None or not pala.operativa:
                continue

            duracion = float(max(5.0, self._rng.normal(mtr_mu, mtr_std)))
            pala.operativa = False
            self._reg('falla_pala_aleatoria', pala=pala_id, duracion=duracion)
            yield self._env.timeout(duracion)
            pala.operativa = True
            pala.tiempo_fuera_servicio_min += duracion
            self._reg('recuperacion_pala', pala=pala_id)

    # ─────────────────────────────────────────────────────────────────────────

    def _bloqueo_via_programado(self, from_id: str, to_id: str,
                                tiempo_min: float, duracion_min: float):
        """Bloquea un tramo de la red vial (Dijkstra lo marcará inaccesible)."""
        yield self._env.timeout(tiempo_min)
        red = getattr(self._mine, 'red_vial', None)
        if red is None or not hasattr(red, 'bloquear_tramo'):
            return
        red.bloquear_tramo(from_id, to_id)
        self._reg('bloqueo_via', from_id=from_id, to_id=to_id, duracion=duracion_min)
        yield self._env.timeout(duracion_min)
        red.desbloquear_tramo(from_id, to_id)
        self._reg('desbloqueo_via', from_id=from_id, to_id=to_id)

    def _reg(self, tipo: str, **datos):
        entrada = {'t': self._env.now, 'tipo': tipo, **datos}
        self.log.append(entrada)
        if self._log_global is not None:
            self._log_global.append(entrada)
