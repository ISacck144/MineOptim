# APU — Asignación y Planificación Unificada

Motor de despacho camión-pala para minería a tajo abierto, adaptado a condiciones andinas (altitud >3,500 msnm, temporada de lluvias, flotas heterogéneas).

**Frase de una línea:** predice tiempos de ciclo con física + ML, reasigna la flota en milisegundos con optimización clásica, y se mantiene estable cuando algo se rompe.

> **Proyecto PERUMEC 2026.** Equipo: 5 estudiantes (4 Ing. Sistemas + 1 Ing. Mecánica), Universidad, Perú.

---

## Aviso sobre los datos

**Todos los datos son sintéticos.** APU no usa ni ha tenido acceso a datos operacionales de ninguna mina real. Los parámetros de equipos (capacidades, consumo, tiempos de carga) están calibrados con valores publicados en los catálogos públicos de los fabricantes (CAT, Komatsu). Los tiempos de viaje y condiciones de la mina son generados por el propio simulador. Esto se hace explícito en cada archivo de configuración.

---

## Instalación y demo en 3 comandos

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Correr la simulación v0 (12 horas simuladas, ShortestQueue)
make v0

# 3. Comparar configuración andina
make v0-andina
```

## ¿Qué esperar en la salida?

```
  Iniciando APU — versión v0
  Config: mina_base.yaml  |  Duración: 12.0 h  |  Semilla: 42

══════════════════════════════════════════════════════
  APU — RESUMEN DE SIMULACIÓN
══════════════════════════════════════════════════════
  Configuración  : Mina Base (Nivel del Mar)
  Despachador    : ShortestQueue
  Duración sim.  : 12.0 h  (720 min simulados)

  PRODUCCIÓN
    Ton. brutas a chancadora :     XX,XXX.X t
    Ton. de fino (Cu) a planta:    X,XXX.XX t
    Ton. a botadero (desmonte):    XX,XXX.X t
    Total transportado        :    XX,XXX.X t
    Ciclos completados        :          XXX

  COLAS (tiempo perdido en ralentí)
    Espera total en palas :      XXX.X min
    Promedio por ciclo    :        X.XX min

  UTILIZACIÓN DE PALAS
    pala_1       : [████████████████░░░░]  XX.X%
    pala_2       : [███████████████░░░░░]  XX.X%
    pala_3       : [████████████░░░░░░░░]  XX.X%

  Tiempo de ejecución real:   X.XXX s
══════════════════════════════════════════════════════

  ✓ Criterio v0 cumplido: X.XXX s < 10 s
```

---

## Estructura del proyecto

```
apu-dispatch/
├── config/           # Escenarios YAML (mina_base, mina_andina)
├── src/apu/
│   ├── sim/          # Motor SimPy: camiones, palas, destinos
│   ├── dispatch/     # Despachadores (5 baselines + APU)
│   ├── physics/      # Rimpull, derateo altitud (v2)
│   ├── ml/           # Random Forest physics-informed (v2)
│   ├── graph/        # Dijkstra sobre red vial (v3)
│   ├── metrics/      # KPIs, Match Factor
│   └── energy/       # Diésel ahorrado, CO₂ (v3)
├── experiments/      # run_ab.py: experimento A/B reproducible
├── dashboard/        # Streamlit: pantalla partida (v2)
└── docs/             # Documentación técnica completa
```

## Versiones

| Versión | Estado | Qué incluye |
|---|---|---|
| **v0** | ✅ Listo | Esqueleto completo: 3 palas, 5 camiones, ShortestQueue, KPIs básicos |
| v1 | En cola | 6 despachadores comparados, Match Factor, tabla + PNG |
| v2 | En cola | Física real, eventos aleatorios, ML, PL, pantalla partida |
| v3 | En cola | Dijkstra, módulo energía, IoT |

## Referencia rápida de comandos

```bash
make install       # pip install -r requirements.txt
make v0            # simulación v0 en mina_base
make v0-andina     # simulación v0 en mina_andina (4,100 msnm)
make dashboard     # streamlit run dashboard/app.py (v2)
make test          # pytest tests/
make clean         # limpiar __pycache__ y resultados
```
