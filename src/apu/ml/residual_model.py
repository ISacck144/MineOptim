import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline


class ResidualForestModel:
    """
    Modelo Physics-Informed para la predicción de tiempos de viaje por tramo.
    
    Formula:
        t_total = t_fisico + f_RF(hora, guardia, clima, congestion, horas_motor, id_tramo)
    """

    def __init__(self, n_estimators: int = 100, max_depth: int = 8, random_state: int = 42):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.random_state = random_state
        self.is_fitted = False

        # Preprocesador para manejar características categóricas y numéricas
        self.categorical_features = ['clima', 'guardia', 'id_tramo']
        self.numeric_features = ['hora_dia', 'congestion', 'horas_motor']

        self.preprocessor = ColumnTransformer(
            transformers=[
                ('cat', OneHotEncoder(handle_unknown='ignore'), self.categorical_features),
                ('num', 'passthrough', self.numeric_features)
            ]
        )

        # Regresor basado en Random Forest
        self.model = Pipeline([
            ('preprocessor', self.preprocessor),
            ('rf', RandomForestRegressor(
                n_estimators=self.n_estimators,
                max_depth=self.max_depth,
                random_state=self.random_state
            ))
        ])

        # Buffer para monitorear el residuo histórico por tramo (Detección de degradación)
        self._residual_history: Dict[str, List[float]] = {}

    def fit(self, historial_tramos: pd.DataFrame) -> 'ResidualForestModel':
        """
        Entrena el modelo usando la diferencia entre el tiempo real y el tiempo físico.

        Columnas esperadas en historial_tramos:
            - 'tiempo_real': Tiempo medido en telemetría (minutos)
            - 'tiempo_fisico': Tiempo teórico por física (minutos)
            - 'hora_dia', 'guardia', 'clima', 'congestion', 'horas_motor', 'id_tramo'
        """
        # Calcular el RESIDUO: y_residual = t_real - t_fisico
        y_residual = historial_tramos['tiempo_real'] - historial_tramos['tiempo_fisico']
        X = historial_tramos[self.categorical_features + self.numeric_features]

        # Ajustar la Random Forest con los residuos
        self.model.fit(X, y_residual)
        self.is_fitted = True

        # Registrar historial inicial de residuos para la detección de degradación
        for _, row in historial_tramos.iterrows():
            tramo_id = str(row['id_tramo'])
            res = float(row['tiempo_real'] - row['tiempo_fisico'])
            if tramo_id not in self._residual_history:
                self._residual_history[tramo_id] = []
            self._residual_history[tramo_id].append(res)

        return self

    def predict(self, tramo_context: Dict) -> Tuple[float, float]:
        """
        Predice el tiempo total de viaje sumando la base física con el residuo de ML.

        Parametros:
            tramo_context (dict): Diccionario con variables de física y contexto actual.
                Ejemplo: {
                    'tiempo_fisico': 12.4,
                    'hora_dia': 14.5,
                    'guardia': 'dia',
                    'clima': 'lluvia_moderada',
                    'congestion': 0.3,
                    'horas_motor': 4500,
                    'id_tramo': 'rampa_03'
                }

        Retorna:
            (tiempo_total_estimado, residuo_estimado)
        """
        t_fisico = tramo_context.get('tiempo_fisico', 0.0)

        if not self.is_fitted:
            # Fallback seguro: Si no se ha entrenado ML, devuelve solo el tiempo físico
            return t_fisico, 0.0

        # Crear DataFrame de un solo registro para la predicción
        df_input = pd.DataFrame([tramo_context])
        X = df_input[self.categorical_features + self.numeric_features]

        # Predecir residuo
        residuo_estimado = float(self.model.predict(X)[0])
        tiempo_total_estimado = max(0.1, t_fisico + residuo_estimado)

        # Actualizar buffer de histórico para monitoreo de vías
        tramo_id = str(tramo_context['id_tramo'])
        if tramo_id not in self._residual_history:
            self._residual_history[tramo_id] = []
        self._residual_history[tramo_id].append(residuo_estimado)

        return tiempo_total_estimado, residuo_estimado

    def detectar_degradacion_via(self, tramo_id: str, ventana: int = 20, umbral_degradacion_min: float = 1.5) -> bool:
        """
        Hallazgo Clave: Detecta si la resistencia a la rodadura de una vía está empeorando.
        Si la media móvil del residuo supera el umbral, indica necesidad de mantenimiento (motoniveladora).

        Parametros:
            tramo_id: Identificador de la ruta o rampa.
            ventana: Número de observaciones recientes a analizar.
            umbral_degradacion_min: Minutos de retraso acumulado tolerados por degradación.

        Retorna:
            True si la vía requiere mantenimiento, False en caso contrario.
        """
        historial = self._residual_history.get(str(tramo_id), [])

        if len(historial) < 5:
            # Datos insuficientes para emitir alerta
            return False

        # Extraer los residuos recientes según la ventana
        residuos_recientes = historial[-ventana:]
        media_movil_residuo = np.mean(residuos_recientes)

        # Si el retraso atribuido a la trocha es alto de forma sostenida
        return bool(media_movil_residuo > umbral_degradacion_min)