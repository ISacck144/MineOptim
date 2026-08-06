# Glosario de Minería a Tajo Abierto

Términos ordenados del más general al más específico. Si lees un documento de APU y encuentras un término que no está aquí, avisar para agregarlo.

---

## Términos operacionales básicos

**Tajo abierto** (open pit)
: Método de minería en que se excava un hoyo a cielo abierto hasta alcanzar el yacimiento. Se construyen rampas en espiral ("bancas") para que los camiones puedan entrar y salir cargados. Alternativa al trabajo subterráneo. La mayoría de las minas de cobre del mundo son tajos abiertos.

**Banco** (bench)
: Cada "escalón" o plataforma horizontal de la pared del tajo. Las palas trabajan sobre un banco; al terminarlo, avanzan al banco inferior. La altura típica es 10–15 m.

**Rampa** (haul road)
: Camino inclinado que sube desde el fondo del tajo hasta la superficie. Las rampas tienen pendientes de 8–12% (por cada 100 m horizontales, sube 8–12 m). Son el factor más importante en el tiempo de viaje y el consumo de diésel.

**Guardia** (shift)
: Turno de trabajo. En minas 24/7 hay tres guardias: mañana (6–14h), tarde (14–22h) y noche (22–6h). Al cambio de guardia se pierden 30–45 minutos de producción (traslado, conteo, briefing). APU modela este efecto.

---

## Equipos

**Pala** (shovel / excavator)
: Excavadora gigante de 500–1,000 toneladas. Carga un camión de 200–300 toneladas en 3–5 minutos. Es el recurso crítico de la mina: si la pala para, todo para. Solo puede cargar un camión a la vez.

**Camión de acarreo** (haul truck)
: Camión de 2–3 pisos de altura que transporta entre 180 y 400 toneladas por viaje. Modelos típicos: CAT 793 (227 t), Komatsu 930E (290 t), Caterpillar 797F (363 t).

**Chancadora** (primary crusher)
: Máquina que tritura la roca mineral en fragmentos manejables para el proceso metalúrgico. Es el primer paso del proceso de concentración. Tiene una capacidad máxima (toneladas/hora); si se la desbasta, se crea una cola; si se la subalimenta, pierde eficiencia.

**Motoniveladora** (grader)
: Equipo que mantiene las rampas en buen estado. Si no nivela regularmente, la resistencia a la rodadura aumenta y los camiones van más lentos. APU detecta este deterioro como un subproducto del modelo ML.

---

## Material extraído

**Mineral** (ore)
: Roca que contiene suficiente metal para ser rentable procesar. Va a la chancadora.

**Desmonte** (waste rock)
: Roca sin suficiente metal. Va al botadero. Su movimiento es costo puro, pero inevitable para acceder al mineral.

**Ley** (grade)
: Concentración de metal en la roca, expresada en porcentaje (Cu) o en gramos por tonelada (oro). Ejemplo: "ley 0.7% Cu" significa 7 kg de cobre por cada tonelada de roca.

**Ley de corte** (cut-off grade)
: Ley mínima para que extraer una roca sea económicamente rentable. Depende del precio del metal, costos operativos y precio del diésel. Típicamente 0.3–0.5% Cu en minas peruanas. La ley de corte separa "mineral" de "desmonte".

**Toneladas de fino** (contained metal)
: La métrica que realmente importa. Si se mueven 1,000 t con ley 0.7% Cu, hay 7 t de cobre fino. Es el numerador del valor económico generado. APU maximiza toneladas de fino, no toneladas brutas.

**Relación de desbroce** (stripping ratio)
: Toneladas de desmonte por tonelada de mineral. Una relación 3:1 significa que hay que mover 3 t de desmonte para extraer 1 t de mineral. Determina cuántos camiones deben ir al botadero vs. a la chancadora.

---

## Logística y planificación

**Botadero** (waste dump)
: Zona de depósito permanente del desmonte. No tiene límite de capacidad (o es muy grande). Los camiones descargan en 1–2 minutos y vuelven.

**Stockpile**
: Zona de acopio temporal de mineral marginal (ley cercana a la de corte). Se guarda para procesarlo cuando el precio del metal sube o cuando la capacidad de la chancadora lo permite.

**Ciclo del camión** (truck cycle)
: Secuencia completa: esperar carga → cargar → viajar cargado → descargar → viajar vacío → esperar carga. Duración típica: 20–35 minutos.

**Match Factor** (MF)
: Razón entre la tasa de llegada de camiones a las palas y la tasa de servicio de las palas. MF < 1 → palas ociosas; MF > 1 → camiones en cola. El objetivo es MF ≈ 1. Ver `docs/01-problema.md`.

**Despachador** (dispatcher)
: Sistema (o persona) que decide, después de cada descarga, a qué pala va cada camión. Esta decisión, tomada miles de veces al día, determina toda la eficiencia de la operación.

---

## Física del transporte

**Rimpull** (fuerza de tracción)
: Fuerza que el motor del camión ejerce en la llanta (rim + pull). Se mide en kgf o kN. Determina si el camión puede subir una rampa con cierta carga a cierta velocidad. Ver `docs/03-modelo-fisico.md`.

**Resistencia a la rodadura** (rolling resistance)
: Fricción entre los neumáticos y la superficie de la rampa. Se expresa como porcentaje del peso del vehículo. En vía seca compactada: 2–3%. En vía mojada o deteriorada: 4–10%. Es la variable que el modelo ML detecta como proxy de degradación de la vía.

**Resistencia total** (total resistance)
: Suma de la pendiente (%) y la resistencia a la rodadura (%). Determina el rimpull necesario y, en consecuencia, la velocidad máxima alcanzable con la potencia disponible.

**Derateo por altitud** (altitude derate)
: Pérdida de potencia del motor diésel a gran altitud por menor densidad del aire. En motores aspirados: ~3% cada 300 m sobre 1,500 msnm. En turbos: pérdida menor que empieza sobre 3,000 msnm. Las minas andinas a 4,100 msnm tienen camiones con 15–20% menos potencia que al nivel del mar. Casi ningún sistema comercial modela esto correctamente.
