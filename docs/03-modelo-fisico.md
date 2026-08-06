# Modelo Físico de Transporte

> **Para el ingeniero mecánico del equipo:** este documento explica exactamente qué supuestos físicos hace APU y qué parámetros necesitan validación con datos reales o tablas del fabricante. Los puntos marcados con ⚠️ **VALIDAR** son los más críticos.

## Variables del modelo

| Variable | Símbolo | Unidad | Descripción |
|---|---|---|---|
| Peso bruto vehicular | PBV | kg | Tara del camión + carga útil |
| Pendiente | G | % | metros de subida por 100 m horizontales |
| Resistencia a la rodadura | RR | % | fricción neumático–vía |
| Resistencia total | RT | % | G + RR |
| Rimpull requerido | R_req | kgf | PBV × RT / 100 |
| Potencia nominal | P_nom | kW | Del catálogo del fabricante |
| Factor de derateo | f_alt | adim. | Fracción de P_nom disponible en altura |
| Potencia efectiva | P_eff | kW | P_nom × f_alt |
| Velocidad | v | km/h | min(v_max, v_potencia) |

## Fórmulas

### 1. Resistencia total

```
RT (%) = G (%) + RR (%)
```

Ejemplo: rampa 9% + vía en buen estado (RR = 0.025 × 100 = 2.5%) → RT = 11.5%

### 2. Rimpull requerido

```
R_req (kgf) = PBV (kg) × RT (%) / 100
```

Ejemplo: CAT 793 cargado = 227,000 kg carga + ~140,000 kg tara ≈ 367,000 kg
R_req = 367,000 × 0.115 = 42,205 kgf

### 3. Velocidad de acarreo

La velocidad real está limitada por dos factores:

```
v = min(v_max, v_potencia)
```

donde `v_potencia` es la velocidad a la que el rimpull disponible (de la curva de tracción del fabricante) iguala al rimpull requerido.

En la versión simplificada de APU (v2):
```
v_potencia ≈ (P_eff × 3,600) / (R_req × 1,000)   [km/h, con P en kW, R en kN]
```

⚠️ **VALIDAR**: la curva de tracción real no es lineal. La versión exacta requiere interpolar la curva rimpull-velocidad del catálogo del fabricante. La fórmula simplificada sobreestima la velocidad en el rango de bajo rimpull.

### 4. Tiempo de viaje por tramo

```
t_tramo (min) = (distancia_km / v_km_h) × 60
```

En v0, este cálculo se reemplaza por la tabla fija del YAML. En v2, usa la física completa.

## Derateo por altitud

Los motores diésel pierden potencia en altura porque hay menos oxígeno.

### Modo aspirado (motores sin turbocompresor)

```
f_alt = 1 - coef_derateo × max(0, altitud_msnm - 1500) / 300
```

Ejemplo a 4,100 msnm con coef = 0.03:
```
f_alt = 1 - 0.03 × (4100 - 1500) / 300 = 1 - 0.03 × 8.67 = 0.74
```
→ el motor tiene el 74% de su potencia nominal.

⚠️ **VALIDAR**: el coeficiente 0.03 es el valor genérico publicado por SAE. Los valores reales varían entre 0.025 y 0.04 según el diseño del motor. Consultar tablas del fabricante (sección "Altitude Performance" del manual de especificaciones).

### Modo turboalimentado

Los turbos compensan parte de la pérdida. La pérdida se nota principalmente sobre los 3,000 msnm:

```
f_alt = 1 - coef_derateo_turbo × max(0, altitud_msnm - 3000) / 300
```

⚠️ **VALIDAR**: el coeficiente para turboalimentados (~0.012 en el YAML) es más agresivo en algunos modelos (hasta 0.02). Consultar la curva específica del motor (CAT C175, QSK60, etc.).

## Resistencia a la rodadura

| Condición de vía | RR (%) | Observación |
|---|---|---|
| Pavimento asfaltado | 1.5–2.0 | No aplica en minería |
| Tierra compactada, seca | 2.0–3.0 | Condición base |
| Tierra compactada, mojada | 4.0–6.0 | Temporada de lluvias |
| Material suelto | 6.0–10.0 | Vía sin mantenimiento |
| Arena profunda | > 10.0 | Emergencia operativa |

⚠️ **VALIDAR**: los valores anteriores son rangos publicados. La RR real depende de la presión de inflado de los neumáticos, el ancho de la vía y el tipo de suelo de la mina específica. Ensayos de campo con GPS + acelerómetro dan la RR real (que es exactamente lo que APU aprende con el modelo ML).

### Degradación de la vía en el tiempo

APU modela que la RR aumenta gradualmente si no hay mantenimiento:

```
RR(t) = RR_base + k_degradacion × t_horas_desde_ultimo_mantenimiento
```

El parámetro `k_degradacion` es configurable en el YAML. El modelo ML detecta este aumento como un crecimiento sistemático del residuo → genera alerta de mantenimiento.

## Parámetros de referencia (valores por defecto en el YAML)

| Equipo | Carga útil | Potencia nominal | Velocidad cargado | Fuente |
|---|---|---|---|---|
| CAT 793F | 227 t | 2,610 kW | ~22 km/h en rampa 8% | Catálogo público CAT |
| Komatsu 930E-4 | 290 t | 2,611 kW | ~20 km/h en rampa 8% | Catálogo público Komatsu |

⚠️ **VALIDAR**: las velocidades dependen del estado de la vía y la altitud. Los valores anteriores son para condiciones de referencia (nivel del mar, vía seca). En condiciones andinas con derateo de altitud, esperar 15–25% menos velocidad.
