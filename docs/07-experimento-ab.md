# Metodología del Experimento A/B

## Principio

Los seis despachadores (5 baselines + APU) corren sobre **exactamente la misma mina, la misma semilla aleatoria y los mismos eventos**. Esto garantiza que cualquier diferencia en el resultado se debe al despachador, no a la suerte.

## Configuración del experimento

| Parámetro | Valor |
|---|---|
| Configuraciones | `mina_base.yaml` + `mina_andina.yaml` |
| Semilla fija | 42 (reproducible con `--seed 42`) |
| Réplicas por despachador | 5 (con semillas 42, 43, 44, 45, 46) |
| Duración por réplica | 12 horas simuladas |
| Eventos aleatorios | Desactivados en v0/v1; activados en v2 |
| Falla de pala programada | Minuto 300 (para medir resiliencia) |

## Despachadores comparados

| Código | Nombre | Referencia |
|---|---|---|
| RND | Random | Alarie & Gamache (2002) — límite inferior |
| NGT | Nearest | Alarie & Gamache (2002) |
| SQ | ShortestQueue | Alarie & Gamache (2002) — el más común |
| SPTF | Shortest Processing Time First | White & Olson (1986) |
| FG | FixedGroup | Práctica real con contratistas |
| **APU** | **Húngaro + PL** | **Este trabajo** |

## Métricas comparadas

| Métrica | Descripción | Unidad | Mejor |
|---|---|---|---|
| `ton_fino` | Toneladas de cobre fino a chancadora | t | Mayor |
| `match_factor` | MF promedio durante la guardia | adim. | Más cercano a 1.0 |
| `tiempo_espera` | Tiempo total en cola de palas | min | Menor |
| `util_palas` | Utilización promedio de palas | % | Mayor |
| `adl` | Latencia de decisión del algoritmo | ms | Menor |

## Análisis estadístico

Con 5 réplicas por despachador, se reporta:
- Media y desviación estándar de cada métrica
- Test de Wilcoxon (no paramétrico) entre APU y cada baseline
- p-value < 0.05 como criterio de significancia

## El experimento de resiliencia (v2)

A los 300 minutos simulados se programa la falla de `pala_2`. Se observa:

1. **FixedGroup**: los camiones asignados a `pala_2` quedan sin destino. El operador debe intervenir manualmente. Tiempo de recuperación: 5–15 min.

2. **ShortestQueue**: los camiones migran solos a las palas con cola más corta. Recuperación: ~2 min.

3. **APU**: el nivel inferior detecta que `pala_2` ya no está operativa. El nivel superior re-resuelve la PL en la próxima iteración (máximo 30 min después, pero puede anticiparse). La brecha de toneladas entre APU y FG se ensancha después del minuto 300 — esto es la imagen clave del pitch.

## Reproducibilidad

Todo experimento tiene un hash de configuración que garantiza que el resultado es reproducible:
```bash
PYTHONPATH=src python -m experiments.run_ab --version v1 --seed 42 --config mina_base
```
El output incluye el hash del YAML para verificar que la configuración no cambió.
