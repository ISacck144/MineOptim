"""
Nivel superior del despachador APU: problema de transporte formulado como
Programación Lineal (PL), resuelto con PuLP cada 30 minutos simulados.

Maximiza las toneladas de fino a planta sujeto a:
  - Capacidad de cada pala
  - Capacidad de la chancadora
  - Ley mínima y máxima de mezcla (restricciones linealizadas)
  - Límite de arsénico en la mezcla
  - Flota disponible (número de camiones)

La linealización de las restricciones de mezcla se documenta en
docs/04-modelo-optimizacion.md. La forma natural es un cociente de
promedios ponderados; se multiplica por el denominador para linearizarla.

Se implementa en v2.
"""

# TODO v2: implementar LPFlowDispatcher
#   - Resolver PL cada 30 min simulados con pulp.LpProblem
#   - Exponer plan como {(shovel_id, dest_id): flujo_ton_h}
#   - Pasar plan al HungarianDispatcher (nivel inferior)
