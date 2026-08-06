# Modelo de Optimización de APU

APU usa una arquitectura de dos niveles que combina optimización global (nivel superior) con asignación local óptima (nivel inferior). La clave está en el término λ que los acopla.

## Nivel Superior: Programación Lineal de Flujos

### Variable de decisión

```
x_sd  [t/h]  =  flujo de material desde la pala s hacia el destino d
```

### Función objetivo

```
max  Σ_s Σ_{d ∈ planta} ley_cu_s · x_sd
```

Maximizamos las toneladas de cobre fino que llegan a la planta. Los flujos al botadero no generan valor y no aparecen en el objetivo (aunque sí en las restricciones).

### Restricciones

**Capacidad de cada pala:**
```
Σ_d x_sd ≤ Cap_s          para todo s
```
Una pala no puede enviar más material del que es capaz de cargar.

**Capacidad de la chancadora:**
```
Σ_s x_{s, chancadora} ≤ Cap_{chancadora}
```
La chancadora tiene un límite de toneladas por hora.

**Ley mínima de mezcla:**
```
Σ_s (L_min - ley_cu_s) · x_{s, chancadora} ≤ 0
```
La mezcla que llega a la chancadora debe tener ley promedio ≥ L_min.

**Linealización de la restricción de mezcla:**
La restricción natural es:
```
(Σ_s ley_cu_s · x_sd) / (Σ_s x_sd) ≥ L_min
```
Esto es no lineal (cociente). Para linearizarla, multiplicamos ambos lados por el denominador (que es ≥ 0):
```
Σ_s ley_cu_s · x_sd ≥ L_min · Σ_s x_sd
Σ_s (ley_cu_s - L_min) · x_sd ≥ 0
Σ_s (L_min - ley_cu_s) · x_sd ≤ 0    [equivalente]
```

La misma linealización aplica para ley máxima y límite de arsénico.

**Ley máxima de mezcla:**
```
Σ_s (ley_cu_s - L_max) · x_{s, chancadora} ≤ 0
```

**Límite de arsénico:**
```
Σ_s (ley_as_s - As_max) · x_{s, chancadora} ≤ 0
```
El arsénico en exceso daña los equipos de flotación y viola normativas ambientales.

**Flota disponible:**
```
Σ_s Σ_d x_sd · T̂_sd / q ≤ N_camiones
```
donde T̂_sd es el tiempo promedio de ciclo estimado (viaje + cola + carga + descarga) y q es la capacidad del camión. Esta restricción garantiza que el plan no exija más camiones de los disponibles.

**No negatividad:**
```
x_sd ≥ 0
```

### Frecuencia y solver

La PL se resuelve cada 30 minutos simulados con PuLP (solver CBC). El resultado es un vector de flujos objetivo que el nivel inferior usará para guiar las asignaciones individuales.

---

## Nivel Inferior: Problema de Asignación (Método Húngaro)

### Problema

Dado un conjunto de camiones disponibles y un conjunto de palas, encontrar la asignación óptima que minimiza el costo total.

### Función de costo

```
c_ij = t̂_viaje(i→j) + t̂_cola(j) + λ · desviación_plan(j)
```

donde:
- `t̂_viaje(i→j)`: tiempo estimado de viaje del camión i a la pala j (modelo ML en v2)
- `t̂_cola(j)`: tiempo estimado de espera en cola de la pala j
- `λ`: parámetro de acoplamiento (configurable en el YAML)
- `desviación_plan(j)`: cuánto se está desviando la pala j de su flujo objetivo

### El término λ: el acoplamiento entre niveles

Sin el término `λ · desviación_plan(j)`, los dos niveles son sistemas desconectados:
- El nivel superior calcula un plan óptimo global.
- El nivel inferior asigna camiones sin considerar ese plan.

El término λ hace que el nivel inferior "sienta" el plan global:
- Si la pala j está enviando menos material del planificado → desviación positiva → costo más alto → el asignador evita enviar más camiones ahí (paradójico al principio, pero correcto: esa pala probablemente tiene un problema; el plan se ajustará en la próxima iteración).

En la práctica, λ se calibra empíricamente. Un valor demasiado alto hace que el nivel inferior ignore el tiempo de viaje; demasiado bajo ignora el plan. El YAML tiene λ = 0.3 como punto de partida.

### Resolución

Se usa `scipy.optimize.linear_sum_assignment` (implementación del algoritmo húngaro de Kuhn-Munkres, O(n³)). Con n ≤ 20 camiones, la latencia de decisión es < 1 ms — esto es lo que APU reporta como ADL (Algorithm Decision Latency).

### Comparación con baselines

| Método | Complejidad | ADL típica | Considera plan global |
|---|---|---|---|
| Random | O(1) | < 0.01 ms | No |
| Nearest | O(n) | < 0.1 ms | No |
| ShortestQueue | O(n) | < 0.1 ms | No |
| SPTF | O(n) | < 0.1 ms | No |
| FixedGroup | O(1) | < 0.01 ms | No |
| **APU (húngaro)** | O(n³) | **< 1 ms** | **Sí (vía λ)** |
| APU (PL nivel superior) | O(PL) | **< 500 ms** | **Sí (cada 30 min)** |

La diferencia de ADL es aceptable porque el nivel inferior se resuelve en cada despacho individual, y el nivel superior se resuelve solo cada 30 minutos simulados.
