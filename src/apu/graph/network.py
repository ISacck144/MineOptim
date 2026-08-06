"""
Grafo de la red vial de la mina.
Nodos: palas, chancadora, botadero, stockpile, intersecciones.
Aristas: tramos con atributos (distancia, pendiente, tipo_superficie).
En v3 se usa con Dijkstra para calcular rutas óptimas con pesos dinámicos
(tiempo predicho por el modelo ML en lugar de distancia fija).
Se implementa en v3.
"""

# TODO v3: class RedVialGrafo con construcción desde YAML y serialización
