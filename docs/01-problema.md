# El Problema del Despacho en Minería a Tajo Abierto

## ¿Qué es una mina a tajo abierto?

Una mina a tajo abierto es un enorme hoyo en la tierra del que se extrae roca mineralizada. A diferencia de las minas subterráneas, todo el trabajo ocurre al aire libre, con equipos gigantes que se ven desde lejos.

El proceso básico es:
1. Se perforan filas de hoyos en la roca y se colocan explosivos.
2. La voladura fragmenta la roca en piezas manejables.
3. **Palas** (excavadoras de 500–1,000 toneladas) cargan esa roca en camiones.
4. Los camiones la transportan al destino correcto.

## El ciclo del camión

```
                 ┌─────────────────────────────────────────────────┐
                 │                                                 │
    ┌──────┐  vacío  ┌──────┐  carga  ┌────────────┐  cargado  ┌──────────┐
    │  Des-│ ───────>│ Cola │ ───────>│   Cargando │ ─────────>│ En ruta  │
    │ pach │         │ pala │  3-5min │  (1 a la   │  8-15min  │ cargado  │
    │      │         └──────┘         │   vez)     │           └──────────┘
    └──────┘                          └────────────┘                 │
       ↑                                                             │
       │                                                             ↓
       │                              DECISIÓN AQUÍ             ┌──────────┐
       │                              ¿A qué pala voy?          │ Descarga │
       └──────────────────────────────────────────────────────── │ 1-2 min  │
                              vacío, 8-12 min                    └──────────┘
```

**Tiempo total de ciclo: 20–35 minutos.**

La decisión de despacho — tomada miles de veces al día — es todo el problema.

## El valor está en el fino

No toda la roca vale lo mismo. La **ley** es el porcentaje de metal en la roca:
- Cobre peruano típico: 0.4% – 1.0% Cu
- **Ley de corte**: si la ley es menor a ~0.4%, extraer esa roca cuesta más de lo que produce → es **desmonte**

Esto define dos destinos completamente distintos:
- **Chancadora** → roca con ley suficiente (**mineral**). Aquí se genera el 100% del ingreso.
- **Botadero** → desmonte. Es costo puro. Hay que moverlo, pero no produce nada.

El KPI que realmente importa no son "toneladas transportadas" sino **toneladas de fino a planta** = toneladas × ley promedio.

## Por qué las colas cuestan dinero

Si la decisión de despacho es mala, ocurren dos cosas malas:

### 1. Camiones en cola en la pala
Un camión de 227 toneladas esperando en ralentí consume entre **8 y 15 litros de diésel por hora**. Si 3 camiones esperan 30 minutos cada uno:
- Costo directo: 3 × 0.5 h × 12 L/h × 4 soles/L = **72 soles perdidos**
- En una guardia de 12 horas, esto se multiplica por cientos de ciclos.

### 2. Pala esperando camión (peor)
Una pala parada es el verdadero problema. La pala es el cuello de botella:
- Costo horario de una pala ≈ USD 1,000–3,000/hora (entre capital, operación y mantenimiento)
- Una pala esperando 10 minutos = USD 167–500 directamente perdidos
- **La pala nunca debe esperar camiones.** Los camiones sí pueden esperar palas.

## El Match Factor

El **Match Factor** (MF) resume todo esto en un número:

```
MF = (N_camiones × t_servicio_pala) / (N_palas × t_ciclo_camion)
```

- **MF < 1**: pocas palas que atender → palas ociosas → el sistema está mal dimensionado o despachado
- **MF = 1**: equilibrio teórico perfecto
- **MF > 1**: muchos camiones para pocas palas → colas → camiones quemando diésel esperando

El objetivo del despachador es mantener MF ≈ 1 **dinámicamente**, porque las condiciones cambian cada minuto (una pala falla, la vía se deteriora, empieza la lluvia).

## El hueco que ataca APU

La literatura identifica cuatro fallas de los sistemas actuales:

| Falla | Consecuencia |
|---|---|
| Decisiones **miopes** (Alarie & Gamache, 2002) | Optimizan el camión actual sin ver el efecto sobre los siguientes |
| Modelos **determinísticos** (LP/MIP) | Las soluciones se vuelven obsoletas en entornos dinámicos |
| Ignoran **eventos imprevistos** | No modelan fallas, atascos, ni degradación de vías |
| Ignoran la **altitud** | Calibrados en Nevada, Chile y Australia; no en los 4,000+ msnm peruanos |

APU ataca los cuatro simultáneamente con una arquitectura de dos niveles:
1. **Nivel superior** (PL): plan global de flujos cada 30 min
2. **Nivel inferior** (método húngaro): asignación óptima en milisegundos

El resultado: producción mayor, colas menores, y resiliencia real ante fallas.
