"""
Módulo de energía: consumo de diésel, costo en soles y emisiones de CO₂.

Fuentes de consumo:
  - Acarreo cargado (máximo consumo, función de potencia y pendiente)
  - Acarreo vacío (menor consumo)
  - Ralentí en cola (constante, 8–15 L/h según equipo)

El ahorro de diésel = diferencia entre ralentí baseline vs APU.
Conversión: 1 L diésel ≈ 2.65 kg CO₂ (factor EPA).
Precio referencia: ~4.0 soles/L (actualizar según mercado).

Se implementa en v3.
"""

# TODO v3: calcular_consumo_guardia(engine, config_energia) -> dict
#   Retorna: litros_acarreo, litros_ralenti, litros_total,
#            soles_total, kg_co2_total
