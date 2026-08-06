# Modelo de Machine Learning: Predictor Physics-Informed de Tiempos de Viaje

## El problema que resuelve

Los tiempos de viaje fijos del YAML (v0) no reflejan la realidad dinámica de una mina:
- A las 2 AM el camión va más rápido (menos tráfico, operario descansado).
- En temporada de lluvias la vía se pone resbaladiza.
- Después de 8 horas de uso sin mantenimiento, la vía se deteriora.
- Al cambio de guardia se pierden 30–45 minutos de productividad real.

El modelo ML aprende estas correcciones **sin necesitar datos históricos de una mina real**, porque los genera él mismo desde el simulador.

## Enfoque: physics-informed

El modelo **no predice el tiempo de viaje absoluto**. Predice el **residuo** de la física:

```
t_tramo_real = t_fisica(pendiente, distancia, carga, altitud) + residuo
residuo = f_RF(hora, guardia, clima, congestión, horas_motor, id_tramo)
```

Por qué esto es mejor que predecir el tiempo directamente:
1. El tiempo físico es siempre un límite inferior plausible → las predicciones nunca son absurdas.
2. El residuo es más estacionario y más fácil de aprender que el tiempo absoluto.
3. Sun et al. (2018) reportan +11.82% de precisión al predecir por tramo vs. por ruta completa.

## Features del residuo

| Feature | Tipo | Descripción |
|---|---|---|
| `hora_sin`, `hora_cos` | numérico | hora del día codificada como sin/cos (cíclica) |
| `es_cambio_guardia` | binario | ventana de ±15 min alrededor del cambio de turno |
| `turno` | categórico | mañana / tarde / noche |
| `lluvia` | binario | condición de lluvia activa |
| `estacion` | categórico | seco / lluvioso (en Perú, bien marcado) |
| `congestion_tramo` | numérico | camiones/km en el tramo en los últimos 5 min simulados |
| `horas_motor` | numérico | horas acumuladas del camión (proxy de desgaste) |
| `id_tramo` | categórico | identificador del tramo (one-hot encoded) |

## Decisiones de diseño (fijadas por la literatura)

Tres decisiones ya validadas en Sun et al. (2018) — no cambiar:

1. **Predecir por tramo (link), no por ruta completa** → +11.82% de precisión
   - Una ruta de pala→chancadora tiene 3–5 tramos. Predecir cada tramo independientemente y sumar es más preciso que predecir la ruta entera.
   
2. **Incluir variables meteorológicas** → +5.13% adicional
   - La lluvia aumenta la resistencia a la rodadura de ~0.025 a ~0.048.
   
3. **Random Forest** (no redes neuronales, no kNN)
   - RF y SVM superan a kNN según Sun et al.
   - RF es interpretable: podemos ver la importancia de cada feature → justificable ante el jurado.
   - No usamos RL porque un despachador real necesita auditar la decisión.

## Entrenamiento

Los datos de entrenamiento los genera el propio simulador:
1. Se corre la simulación con eventos aleatorios (v2) durante N guardias.
2. Se calcula el residuo = t_real_tramo - t_fisica_tramo para cada viaje.
3. Se entrena el RF con estos residuos.
4. El RF predice residuos futuros → se suman a t_fisica → estimación de t_real.

**Importante**: todos los datos son sintéticos. Esto es explícito en el README.

## Hallazgo: detector de degradación de vía

Este es el resultado más sorprendente del modelo, y es un subproducto, no una función planeada.

Si la resistencia a la rodadura de un tramo aumenta (porque nadie pasó la motoniveladora), el tiempo de viaje por ese tramo aumenta → el residuo del modelo crece de forma sistemática.

Un detector simple:
```python
media_movil = promedio(residuos[-20:])  # últimas 20 observaciones del tramo
if media_movil > umbral:
    emitir_alerta(f"Orden de trabajo: mantenimiento de vía en {tramo_id}")
```

El umbral se calibra como percentil 95 de la distribución de residuos histórica del tramo.

El resultado es una **orden de trabajo automática para la motoniveladora** — algo que ningún sistema de despacho comercial hace como efecto secundario de su modelo predictivo.
