"""
Ingeniería de features para el predictor de residuo physics-informed.

Features del residuo (t_real - t_fisica) por tramo:
  - hora_del_dia (cíclica: sin/cos)
  - es_cambio_de_guardia (bool: ventana de 15 min alrededor del cambio)
  - turno (mañana / tarde / noche)
  - clima (lluvia, neblina, seco)
  - congestion_tramo (camiones/km en el tramo en los últimos 5 min)
  - horas_motor_camion (proxy de desgaste del vehículo)
  - id_tramo (categorical encoded)

Decisiones validadas en Sun et al. (2018):
  - Predecir por tramo, no por ruta completa → +11.82% precisión
  - Incluir variables meteorológicas → +5.13%
  - Random Forest supera a kNN y SVM

Se implementa en v2.
"""

# TODO v2: class FeatureExtractor
