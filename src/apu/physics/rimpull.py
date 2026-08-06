"""
Cálculo de Rimpull y velocidad de acarreo según física del vehículo.

Fórmulas (ver docs/03-modelo-fisico.md):
  RT (%) = pendiente (%) + resistencia_rodadura (%)
  Rimpull requerido (kgf) = PBV (kg) × RT / 100
  v = min(v_max, v_de_potencia_efectiva)

Se implementa en v2.
VALIDAR parámetros con tablas del fabricante (CAT, Komatsu).
"""

# TODO v2: implementar calcular_velocidad(camion, tramo, altitud_msnm, config)
