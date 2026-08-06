# Arquitectura IoT: ¿De Dónde Vienen los Datos en una Mina Real?

> Este módulo responde la pregunta más frecuente de los jurados técnicos:
> "¿cómo obtendrías estos datos en producción?"

## El problema de los datos en minería

APU usa en producción real: posición de cada camión, tiempo de viaje por tramo, estado de la vía, condiciones climáticas. En una mina real, esta información viene de una red de sensores distribuidos.

## Arquitectura propuesta

```
┌─────────────────────────────────────────────────────────────────────────┐
│  EQUIPO EN CAMPO                                                         │
│                                                                          │
│  Cada camión lleva:                                                      │
│  ┌────────────────┐   ┌──────────────────┐   ┌───────────────────────┐  │
│  │  GPS (10 Hz)   │   │  Acelerómetro    │   │  CAN Bus del motor    │  │
│  │  posición      │   │  (vibraciones,   │   │  (RPM, temp, consumo  │  │
│  │  velocidad     │   │   estado vía)    │   │   de combustible)     │  │
│  └────────────────┘   └──────────────────┘   └───────────────────────┘  │
│           │                    │                        │                │
│           └────────────────────┴────────────────────────┘                │
│                                │                                         │
│                         ┌──────────────┐                                 │
│                         │  ESP32 / RPi │   microcontrolador a bordo      │
│                         │  procesa +   │   (filtra, comprime, transmite) │
│                         │  transmite   │                                 │
│                         └──────────────┘                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                          MQTT over LTE/WiFi mesh
                                │
┌─────────────────────────────────────────────────────────────────────────┐
│  INFRAESTRUCTURA DE RED                                                  │
│                                                                          │
│  ┌──────────────────┐     ┌────────────────┐     ┌──────────────────┐  │
│  │  MQTT Broker     │ --> │  Message Queue │ --> │  Time-series DB  │  │
│  │  (Mosquitto)     │     │  (Kafka/Redis) │     │  (InfluxDB)      │  │
│  │  en edge server  │     │                │     │                  │  │
│  └──────────────────┘     └────────────────┘     └──────────────────┘  │
│                                                          │               │
│                                                   ┌──────────────┐      │
│                                                   │  APU Engine  │      │
│                                                   │  (este repo) │      │
│                                                   └──────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
```

## Sensores y su rol en APU

| Sensor | Dato | Uso en APU |
|---|---|---|
| GPS (10 Hz) | Posición, velocidad | Tiempo real de viaje por tramo; alimenta el modelo ML |
| Acelerómetro (3 ejes) | Vibraciones de la vía | Proxy de estado de la vía (resistencia a la rodadura) |
| CAN Bus del motor | RPM, consumo, temperatura | Horas-motor, derateo real por altitud, consumo de diésel |
| Sensor de presión neumáticos | TPMS | Resistencia a la rodadura (el inflado afecta directamente) |
| Estación meteorológica (mina) | lluvia, temperatura, viento | Feature climática del modelo ML |

## Protocolo MQTT

Cada camión publica en el tópico:
```
mina/{mina_id}/truck/{truck_id}/telemetry
```

Payload JSON cada 10 segundos:
```json
{
  "ts": "2026-08-06T10:32:15Z",
  "truck_id": "truck_04",
  "lat": -14.8234,
  "lon": -71.3452,
  "alt": 4105,
  "vel_kmh": 18.3,
  "payload_ton": 290,
  "estado": "cargado_en_ruta",
  "tramo_id": "pala_2_chancadora_seg3",
  "rpm": 1850,
  "temp_motor_c": 87,
  "consumo_l_h": 245,
  "lluvia": false
}
```

## ¿Por qué este enfoque es realista?

Las minas peruanas grandes (Las Bambas, Antapaccay, Quellaveco) ya tienen:
- Redes WiFi mesh en las rampas principales (para telemetría y comunicación)
- GPS en todos los camiones (requerido por seguros y por los OEM)
- Sistemas de manejo de flota (FMS) comerciales (Wenco, Modular Mining, Leica)

APU reemplaza la capa de decisión de esos FMS, no la telemetría. Los datos ya existen; el diferencial es cómo se usan.

## Componente de hardware para prototipo (costo < USD 200)

| Componente | Función | Costo aprox. |
|---|---|---|
| ESP32 con GPS Neo-8M | Posición + transmisión MQTT | USD 25 |
| Acelerómetro MPU-6050 | Estado de la vía | USD 5 |
| Módulo SIM800L (4G) | Transmisión donde no hay WiFi | USD 15 |
| Batería LiPo 3Ah | Autonomía 8h sin carga | USD 20 |
| **Total prototipo** | | **USD 65** |

Un prototipo completo en un vehículo de prueba valdría menos de lo que cuesta una hora de operación de la pala.
