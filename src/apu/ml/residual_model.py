"""
Modelo physics-informed de predicción de tiempos de viaje por tramo.

  t_tramo = t_fisica(pendiente, distancia, carga, altitud)
           + f_RF(hora, guardia, clima, congestión, horas_motor, id_tramo)

El modelo NO predice el tiempo absoluto, sino el RESIDUO de la física.
Esto garantiza que las predicciones sean físicamente plausibles aunque
el modelo ML no haya visto ese tramo específico.

Hallazgo clave implementado: si el residuo de un tramo crece de forma
sostenida (media móvil > umbral), la resistencia a la rodadura está
aumentando → la vía se está degradando → emitir alerta de mantenimiento.

Se implementa en v2.
"""

# TODO v2: class ResidualForestModel
#   - fit(historial_tramos)
#   - predict(tramo, context) -> residuo_estimado
#   - detectar_degradacion_via(tramo_id, ventana=20) -> bool
