"""
Match Factor (MF): razón entre la tasa de llegada de camiones a las palas
y la tasa de servicio de las palas.

  MF < 1  → palas ociosas (cuello de botella son los camiones)
  MF = 1  → equilibrio perfecto (teórico)
  MF > 1  → camiones en cola (cuello de botella son las palas)

Para flotas heterogéneas, se usa la formulación de Atkinson (1992):
  MF = (N_c × t_ciclo_pala) / (N_p × t_ciclo_camion)

donde t_ciclo_pala incluye el tiempo de carga de la flota completa.

Se implementa con datos reales en v1.
"""

# TODO v1: calcular_match_factor(engine) -> float
