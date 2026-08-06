"""
Predictor physics-informed del residuo de tiempo de viaje por tramo.

  t_real = t_fisica + residuo
  residuo ~ RF(features del contexto)

El modelo NO predice el tiempo absoluto, sino el delta sobre la física.
Esto garantiza predicciones físicamente plausibles y mejora la robustez
ante tramos nunca vistos (el residuo estimado es 0, que es la física pura).

Hallazgo clave: si el residuo medio de un tramo crece de forma sostenida
(media móvil de ventana 20 > umbral × t_fisica), la resistencia a la
rodadura está aumentando → vía en deterioro → emitir alerta.

Fuente metodológica: Sun et al. (2018) "Mining Truck Dispatch Based on
Physics-Informed Machine Learning". Sección 4.2.
"""

import numpy as np

try:
    from sklearn.ensemble import RandomForestRegressor
    _SKL_OK = True
except ImportError:
    _SKL_OK = False


class ResidualForestModel:
    """
    Wrapper sobre RandomForestRegressor adaptado al dominio de despacho.

    Flujo de datos:
      1. El motor llama a registrar() en cada ciclo de camión.
      2. Después del período de burn-in, el motor llama a fit().
      3. Desde entonces, predict() devuelve el residuo estimado.
      4. detectar_degradacion() puede llamarse en cualquier momento.
    """

    def __init__(self, burn_in_samples: int = 30, threshold: float = 0.15,
                 n_estimators: int = 50, seed: int = 7):
        self._burn_in  = burn_in_samples
        self._thr      = threshold         # fracción del t_fisica para alertar
        self._seed     = seed
        self._n_est    = n_estimators

        self._datos: list[tuple] = []      # (features, residuo)
        self._historial: dict[str, list]  = {}   # tramo_id → [residuos]
        self._modelo = None
        self.entrenado = False
        self.alertas: list[dict] = []

    # ─────────────────────────────────────────────────────────────────────────
    # API principal
    # ─────────────────────────────────────────────────────────────────────────

    def registrar(self, tramo_id: str, t_fisica: float, t_real: float,
                  features: list[float], t_sim: float = 0.0):
        """Registra un viaje completado para entrenamiento / detección."""
        residuo = t_real - t_fisica
        self._datos.append((features, residuo))
        if tramo_id not in self._historial:
            self._historial[tramo_id] = []
        self._historial[tramo_id].append((t_sim, t_fisica, residuo))

        # Auto-detectar degradación cada 10 registros nuevos por tramo
        if len(self._historial[tramo_id]) % 10 == 0:
            self._chequear_degradacion(tramo_id, t_sim)

    def fit(self) -> bool:
        """Entrena el RF con los datos acumulados. Retorna True si tuvo éxito."""
        if len(self._datos) < self._burn_in or not _SKL_OK:
            return False
        X = [d[0] for d in self._datos]
        y = [d[1] for d in self._datos]
        self._modelo = RandomForestRegressor(
            n_estimators=self._n_est, random_state=self._seed, n_jobs=-1
        )
        self._modelo.fit(X, y)
        self.entrenado = True
        return True

    def predict(self, features: list[float]) -> float:
        """Retorna el residuo estimado en minutos (0.0 si no está entrenado)."""
        if not self.entrenado or self._modelo is None:
            return 0.0
        return float(self._modelo.predict([features])[0])

    # ─────────────────────────────────────────────────────────────────────────
    # Detección de degradación de vía
    # ─────────────────────────────────────────────────────────────────────────

    def _chequear_degradacion(self, tramo_id: str, t_sim: float, ventana: int = 20):
        hist = self._historial[tramo_id]
        if len(hist) < ventana:
            return

        ultimos = hist[-ventana:]
        t_fisica_media = np.mean([h[1] for h in ultimos])
        residuo_media  = np.mean([h[2] for h in ultimos])

        if t_fisica_media > 0 and residuo_media / t_fisica_media > self._thr:
            alerta = {
                't_sim': t_sim,
                'tramo': tramo_id,
                'residuo_relativo': residuo_media / t_fisica_media,
                'mensaje': (
                    f"[ALERTA ML] Tramo '{tramo_id}': residuo promedio "
                    f"{residuo_media:.2f} min ({residuo_media/t_fisica_media*100:.1f}% "
                    f"sobre física). Posible deterioro de vía."
                ),
            }
            # Emitir alerta solo una vez por tramo por hora simulada
            ya_emitida = any(
                a['tramo'] == tramo_id and abs(a['t_sim'] - t_sim) < 60
                for a in self.alertas
            )
            if not ya_emitida:
                self.alertas.append(alerta)

    def resumen_alertas(self) -> str:
        if not self.alertas:
            return "  [ML] Sin alertas de degradación de vía."
        lineas = ["  [ML] Alertas de degradación detectadas:"]
        for a in self.alertas:
            lineas.append(f"    t={a['t_sim']:6.1f} min | {a['mensaje']}")
        return "\n".join(lineas)
