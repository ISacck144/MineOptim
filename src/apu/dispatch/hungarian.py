"""
Nivel inferior del despachador APU: problema de asignación resuelto
con el método húngaro (scipy.optimize.linear_sum_assignment).

Función de costo por par (camión i, pala j):
  c_ij = t_viaje(i→j) + t_cola(j) + λ · desviación_del_plan(j)

El término λ es lo que acopla los dos niveles: sin él, el nivel inferior
ignoraría completamente el plan de producción del nivel superior (PL).
λ es configurable en el YAML (despacho.lambda_acoplamiento).

Se implementa en v2.
"""

# TODO v2: implementar HungarianDispatcher
#   - Recibe el plan (x_sd) del nivel superior (LPFlowDispatcher)
#   - Resuelve el problema de asignación con scipy.optimize.linear_sum_assignment
#   - Mide y registra la latencia de decisión (ADL)
