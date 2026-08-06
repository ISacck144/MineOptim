"""
Red vial del simulador APU.

RedVial      (v0/v1/v2) — tabla plana tiempos_viaje_min del YAML.
RedVialDijkstra (v3)    — grafo ponderado con Dijkstra; soporta bloqueos
                          dinámicos de tramos (mantenimiento, derrumbes).

La interfaz pública es idéntica para ambas clases: tiempo_viaje(origen, destino).
El engine elige la clase según el YAML (red_vial_v3 presente → Dijkstra).
"""

import heapq

# Valor centinela: tramo inaccesible (bloqueado o sin ruta)
TIEMPO_INACCESIBLE = 9_999.0


class RedVial:
    """
    v0/v1/v2: tabla plana de tiempos leída desde el YAML.
    """

    def __init__(self, tiempos: dict):
        self._tiempos = tiempos

    def tiempo_viaje(self, origen_id: str, destino_id: str) -> float:
        if origen_id == destino_id:
            return 0.0
        try:
            return float(self._tiempos[origen_id][destino_id])
        except KeyError:
            raise KeyError(
                f"Tiempo de viaje no definido: '{origen_id}' → '{destino_id}'. "
                f"Agrega la entrada en tiempos_viaje_min."
            )


class RedVialDijkstra:
    """
    v3: grafo dirigido con pesos dinámicos.

    Los nodos son palas, destinos e intersecciones.
    Las aristas tienen peso = tiempo de viaje en minutos (ida y vuelta pueden diferir).
    Los factores dinámicos permiten simular bloqueos y degradación de vías.
    """

    def __init__(self, cfg_red: dict):
        """
        cfg_red : sección 'red_vial_v3' del YAML.
          nodos   : {node_id: {pos_x, pos_y}}
          aristas : [{from, to, tiempo_ida_min, tiempo_vuelta_min, id?}]
        """
        self._nodos: dict[str, dict]  = cfg_red.get('nodos', {})
        self._aristas_raw: list[dict] = cfg_red.get('aristas', [])

        # Grafo: {from_id: {to_id: t_base_min}}
        self._grafo: dict[str, dict[str, float]] = {}

        # Factores dinámicos: {(from_id, to_id): multiplicador}
        self._factores: dict[tuple, float] = {}

        self._construir_grafo()

    # ─────────────────────────────────────────────────────────────────────────
    # Construcción
    # ─────────────────────────────────────────────────────────────────────────

    def _construir_grafo(self):
        for a in self._aristas_raw:
            f = a['from']
            t = a['to']
            t_ida    = float(a['tiempo_ida_min'])
            t_vuelta = float(a.get('tiempo_vuelta_min', t_ida))

            self._grafo.setdefault(f, {})[t] = t_ida
            self._grafo.setdefault(t, {})[f] = t_vuelta

    # ─────────────────────────────────────────────────────────────────────────
    # API pública
    # ─────────────────────────────────────────────────────────────────────────

    def tiempo_viaje(self, origen_id: str, destino_id: str) -> float:
        """
        Dijkstra desde origen hasta destino.
        Retorna TIEMPO_INACCESIBLE si no hay ruta disponible.
        """
        if origen_id == destino_id:
            return 0.0

        dist: dict[str, float] = {}
        for n in self._grafo:
            dist[n] = TIEMPO_INACCESIBLE
        dist[origen_id] = 0.0

        heap = [(0.0, origen_id)]

        while heap:
            d, u = heapq.heappop(heap)
            if d > dist[u] + 1e-9:
                continue
            if u == destino_id:
                return dist[u]
            for v, t_base in self._grafo.get(u, {}).items():
                factor = self._factores.get((u, v), 1.0)
                if factor >= TIEMPO_INACCESIBLE:
                    continue
                t_edge = t_base * factor
                nueva_dist = dist[u] + t_edge
                if nueva_dist < dist.get(v, TIEMPO_INACCESIBLE):
                    dist[v] = nueva_dist
                    heapq.heappush(heap, (nueva_dist, v))

        return TIEMPO_INACCESIBLE

    def bloquear_tramo(self, from_id: str, to_id: str):
        """Hace inaccesible el tramo (y el inverso si existe)."""
        self._factores[(from_id, to_id)] = TIEMPO_INACCESIBLE
        if to_id in self._grafo and from_id in self._grafo.get(to_id, {}):
            self._factores[(to_id, from_id)] = TIEMPO_INACCESIBLE

    def desbloquear_tramo(self, from_id: str, to_id: str):
        self._factores.pop((from_id, to_id), None)
        self._factores.pop((to_id, from_id), None)

    def actualizar_factor(self, from_id: str, to_id: str, factor: float):
        """factor=1 normal, factor=1.5 lluvia fuerte, factor=inf bloqueado."""
        self._factores[(from_id, to_id)] = factor

    # ─────────────────────────────────────────────────────────────────────────
    # Utilidades para el dashboard
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def nodos(self) -> dict:
        return self._nodos

    @property
    def aristas(self) -> list:
        return self._aristas_raw

    def coord(self, node_id: str) -> tuple[float, float]:
        """Retorna (pos_x, pos_y) de un nodo, o (0,0) si no existe."""
        n = self._nodos.get(node_id, {})
        return float(n.get('pos_x', 0)), float(n.get('pos_y', 0))
