"""
Derateo de potencia del motor por altitud sobre el nivel del mar.

Dos modos configurables en el YAML (motor.tipo_aspiracion):
  - 'aspirado':       ~3% de pérdida por cada 300 m sobre 1,500 msnm
  - 'turboalimentado': pérdida menor, empieza a notarse sobre ~3,000 msnm

El coeficiente exacto debe validarse contra las curvas de potencia del
fabricante específico del equipo (CAT, Komatsu, Liebherr, etc.).

Se implementa en v2.
"""

# TODO v2: implementar factor_derateo(altitud_msnm, tipo_aspiracion, config) -> float
#   Retorna un escalar en [0, 1] que multiplica la potencia nominal.
