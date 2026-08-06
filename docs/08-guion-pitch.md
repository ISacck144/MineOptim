# Guion de Pitch — 5 Minutos

> Ensayar en voz alta. Cronometrar. Ajustar.

---

## Minuto 1: El problema (0:00–1:00)

**[Abrir con el dashboard: dos contadores de toneladas]**

"Están viendo dos minas idénticas corriendo al mismo tiempo. Misma cantidad de palas, mismos camiones, mismo mineral. La única diferencia es cómo se decide a qué pala va cada camión cuando termina de descargar."

"En una mina peruana de cobre a tajo abierto, esa decisión se toma 500 veces por día. Si se toma mal, los camiones —que pesan 300 toneladas y consumen 250 litros de diésel por hora— se quedan esperando en cola. La pala, que cuesta USD 2,000 la hora, espera camión."

"El acarreo es entre el 45% y el 60% del costo operativo total de una mina. Y en Perú operamos a 4,000 metros sobre el nivel del mar, donde casi ningún sistema comercial está calibrado."

---

## Minuto 2: La solución (1:00–2:00)

**[Mostrar diagrama de dos niveles]**

"APU —Asignación y Planificación Unificada— resuelve esto con dos capas de optimización."

"Cada 30 minutos, una Programación Lineal calcula el plan global: qué flujo de material debe ir de cada pala a la chancadora para maximizar el cobre fino y respetar los límites de mezcla."

"Cada vez que un camión termina de descargar, un problema de asignación resuelto con el método húngaro dice exactamente a qué pala va. La decisión tarda menos de un milisegundo."

"El modelo también predice cuánto tardará el viaje usando física del motor corregida con Machine Learning. Y como efecto secundario, detecta cuándo una vía se está deteriorando y genera automáticamente una orden de trabajo para la motoniveladora."

---

## Minuto 3: Los resultados (2:00–3:00)

**[Mostrar tabla comparativa]**

"Comparamos APU contra los cinco métodos de referencia de la literatura. Misma mina, misma semilla, 12 horas simuladas."

"APU produce X% más toneladas de fino que el método de grupo fijo —que es el que se usa cuando hay varios contratistas de acarreo. La diferencia equivale a Y toneladas de cobre por guardia."

**[Mostrar curvas post-falla de pala]**

"Y aquí está el resultado más importante: a los 300 minutos simulamos una falla de pala. FixedGroup se atasca porque los camiones no tienen a dónde ir. APU reasigna la flota en segundos. La brecha se ensancha exactamente cuando más importa."

---

## Minuto 4: El diferencial andino (3:00–4:00)

**[Mostrar comparativa mina_base vs. mina_andina]**

"Los sistemas comerciales —Wenco, Modular Mining— fueron calibrados en Nevada, Chile y Australia. No modelan el derateo de potencia por altitud. No modelan cómo la temporada de lluvias aumenta la resistencia a la rodadura."

"En condiciones andinas, nuestro modelo de física muestra que los camiones tienen hasta 25% menos potencia y van 20% más lentos que al nivel del mar. Si el despachador no sabe esto, asigna camiones a palas como si pudieran llegar en 9 minutos, cuando en realidad tardan 13. El plan se vuelve obsoleto antes de ejecutarse."

"APU tiene los parámetros andinos configurados en el YAML. Y son los únicos que el ingeniero mecánico del equipo puede validar con las tablas del fabricante."

---

## Minuto 5: Cierre y escalabilidad (4:00–5:00)

"APU es software abierto. Corre en una laptop sin internet —lo estamos haciendo ahora mismo. Los datos los genera el propio simulador, calibrado con catálogos públicos de equipos. Nada de lo que ven aquí fue inventado ni tomado de una mina real."

"En producción, los datos vendrían de los GPS y sensores que ya llevan los camiones. APU reemplaza solo la capa de decisión de los sistemas de manejo de flota existentes."

"El prototipo de hardware para validación en campo cuesta menos de USD 70 por camión."

**[Mostrar los dos contadores de toneladas una última vez]**

"La diferencia entre estas dos columnas —en 12 horas simuladas— es la diferencia entre ganar y perder dinero en el turno de noche. Gracias."

---

## Preguntas frecuentes del jurado

**"¿Los datos son reales?"**
No. Son sintéticos, generados por nuestro simulador, calibrado con parámetros públicos de equipos. Esto está explícito en el README y en toda la documentación. La validación con datos reales es el siguiente paso post-hackathon.

**"¿Por qué no usan RL?"**
Un despachador industrial necesita auditar la decisión: ¿por qué se asignó ese camión a esa pala? El RL no puede responder esa pregunta. La Programación Lineal y el método húngaro sí. Además, la literatura reciente (Hazrathosseini, 2024) señala la baja interpretabilidad del RL como su principal limitación operativa.

**"¿Cómo escala a flotas más grandes?"**
El método húngaro es O(n³) en el número de camiones. Con n=50, la decisión sigue siendo < 10 ms. La PL escala con el número de palas y destinos, no de camiones. En minas grandes con 100+ camiones, se usa una heurística de descomposición (Lagrangiana), que ya está en la literatura.
