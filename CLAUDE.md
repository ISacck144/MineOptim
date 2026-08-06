# CLAUDE.md — Contexto para Futuras Sesiones

Proyecto APU para PERUMEC 2026. Lee esto antes de tocar cualquier archivo.

## Decisiones de diseño irrevocables

1. **Sin RL.** El despachador debe ser auditable. Un operador de mina necesita saber POR QUÉ se asignó ese camión a esa pala. RL no puede responder esa pregunta.

2. **Sin datos reales.** Todos los datos son sintéticos, generados por el simulador. Jamás presentar datos sintéticos como si fueran mediciones de campo.

3. **Rebanadas verticales.** Cada versión corre de punta a punta. No construir módulos aislados que esperan integrarse después.

4. **Sin sobre-ingeniería.** Es un hackathon. Simple que corre > elegante que no corre.

## Arquitectura de dos niveles (el corazón del sistema)

```
Nivel superior (PL)           → cada 30 min simulados
  Resuelve: ¿qué flujo (t/h) debe ir de cada pala a cada destino?
  Herramienta: PuLP + CBC
  Output: plan {(shovel_id, dest_id): flujo_ton_h}

Nivel inferior (Húngaro)      → en cada despacho individual (< 1 ms)
  Resuelve: ¿a qué pala va este camión específico?
  Herramienta: scipy.optimize.linear_sum_assignment
  Costo: c_ij = t_viaje + t_cola + λ·desviación_plan
  λ es lo que acopla los dos niveles. Sin λ son sistemas desconectados.
```

## Dependencias exactas (no agregar sin consultar)

```
simpy, numpy, pandas, scipy, scikit-learn, pulp, matplotlib, pyyaml, streamlit
```

## Convenciones de código

- Variables: inglés (truck, shovel, mine_state)
- Comentarios y docstrings: español
- Unidades: minutos para tiempos de viaje, toneladas para masa, km/h para velocidad
- Configuración: siempre en YAML, nunca hardcodeada

## Estado de las versiones

- **v0** ✅: SimPy funcionando, ShortestQueue, KPIs básicos
- **v1** ✅: 5 baselines + húngaro, Match Factor, tabla comparativa + PNG
           APU +7.6% ton.fino vs ShortestQueue (sin eventos)
- **v2** ✅: física estocástica, eventos (falla pala_2 t=300), ML, LP+Húngaro
           APU +10.3% ton.fino con falla activa — brecha se ensancha durante la falla
- **v3** ✅: Dijkstra en red vial (grafo), energía (L/t_fino), bloqueo de tramos
           APU +13.7% (mina_base) / +14.8% (mina_andina) vs ShortestQueue
           Dashboard Streamlit en dashboard/app.py

## Qué NO hacer

- No cambiar el enfoque del ML de physics-informed a predicción directa
- No agregar RL bajo ningún pretexto
- No hardcodear parámetros que deberían estar en YAML
- No construir v2 sin que v1 esté validado
- No omitir el aviso de "datos sintéticos" en ningún documento público

## Archivos críticos

| Archivo | Rol |
|---|---|
| `src/apu/sim/engine.py` | Motor SimPy — el ciclo del camión es el corazón |
| `src/apu/dispatch/baselines.py` | Los 5 métodos de referencia de la literatura |
| `src/apu/dispatch/hungarian.py` | Nivel inferior de APU (v2) |
| `src/apu/dispatch/lp_flow.py` | Nivel superior de APU (v2) |
| `config/mina_base.yaml` | Escenario de referencia |
| `config/mina_andina.yaml` | Escenario diferencial andino |
| `experiments/run_ab.py` | Punto de entrada principal |

## Parámetros físicos pendientes de validación (tarea del Ing. Mecánico)

- `coef_derateo_por_300m` en mina_andina.yaml → validar con tablas del fabricante
- `coef_lluvia` en rodadura → validar con ensayos de campo
- `degradacion_por_hora` → calibrar con datos de mantenimiento real
