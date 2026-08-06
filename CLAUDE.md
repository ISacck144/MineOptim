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
- **v1** pendiente: 5 baselines + húngaro, Match Factor, tabla comparativa + PNG
- **v2** pendiente: física real, eventos aleatorios, ML, PL, Streamlit
- **v3** pendiente: Dijkstra, energía, IoT

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
