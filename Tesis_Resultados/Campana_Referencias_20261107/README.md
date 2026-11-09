# Campaña de referencia a 3 GHz

Campaña nueva, separada de los resultados históricos. Los valores son evaluaciones de modelos publicados; no mediciones propias de materiales reales.

## Parámetros y fuentes

- Vacío: εr=1; σ=0.
- Concreto: εr=5.24; σ=0.10910539375856032 S/m, UIT-R P.2040-4 (2025), cuadro 3, rama 1–100 GHz: https://www.itu.int/rec/R-REC-P.2040-4-202509-I/en
- Agua marina: εr=70.31403283336333; σ equivalente=6.37211202115965 S/m. UIT-R P.527-6 (2021), 20 °C y 35 g/kg: https://www.itu.int/rec/R-REC-P.527-6-202109-I/en
- Músculo: εr=52.05799768655297; σ equivalente=2.142139799739875 S/m. IT’IS V5.0, tabla principal de Gabriel: https://doi.org/10.13099/VIP21000-05-0

`materiales.csv` conserva precisión completa. `parametros_referencia.py` reproduce su cálculo; `procedencia_materiales.json` identifica coeficientes y hashes de los datos consultados. La conductividad equivalente incluye la pérdida dieléctrica: no se añade una segunda vez. El modelo en Meep es no dispersivo en ε y óhmico, equivalente en la frecuencia central; no se interpreta su transitorio como un modelo de banda ancha de tejido/agua.

## Diseño registrado antes de ejecutar

`ejecutar_campana.py` genera `plan.json` con todos los casos. Onda plana: cuatro medios a 5 y 10 px/mm. Lámina vacío–material–vacío: tres materiales, cuatro espesores y mallas 5/10/20 px/mm; 30 mm de concreto y 7 mm de agua/músculo se reservaron como casos de comprobación independiente, sin calibrar parámetros con ellos. Se incluyeron vacío y controles de espesor PML.

Monopolo: comparación común 5 px/mm, agua 5/10/20/40, músculo 5/10/20, concreto 5/10. Los controles PML usan 3λ frente a 2λ. Cada corrida proporciona simultáneamente perfil y balance anular; así no se duplica una simulación para extraer otra magnitud. Se conservaron la geometría y el escalado con λ del programa previo. El arranque suave y los campos magnéticos sincronizados reducen contaminación transitoria y desfase temporal. La muestra radial se evaluó en coordenadas físicas explícitas.

La fuente no se calibró en SI. Se guardaron campos complejos, flujo con signo, potencias normalizadas y tiempos. En lámina se calculó la reflexión sustrayendo los campos de una corrida de vacío idéntica, la transmisión con flujo saliente y la absorción con una integral independiente de Joule. Se contrastaron R, T y A con la solución analítica de una lámina plana. La absorción no se definió como 1−R−T.

Para comparar mallas del monopolo se fijó un modelo lineal M0 en la ventana física correspondiente. La pendiente quedó sin restricción de signo, incluso en vacío. Se guardaron IC condicionales por bloques, residuos diagnosticados, sensibilidad de ventana y cambio temporal. Un ajuste inadecuado no se convierte en válido por coincidir con la teoría. La variabilidad material no se inventó ni se confundió con el IC del ajuste.

La identidad de constantes se impuso mediante μ0=1/(ε0 c²). ε0=8.8541878128e−12 F/m, c=299792458 m/s. Longitud de referencia a=1 mm, tiempo a/c; σD=σ a/(ε0 c εr). La atenuación en dB/mm se obtuvo con 20/ln(10), sin redondear a 8.686.

## Ejecución, recursos y reanudación

En VS Code/Ubuntu ejecutar la tarea `Tesis: campana con fuentes verificadas`. Se utiliza el entorno Meep existente, un hilo y prioridad nice=15. La cola ejecuta un solo proceso. Se registra consumo cada 30 s y se interrumpe el caso si RSS supera 5 GiB o MemAvailable cae de 700 MiB; entonces se detiene la cola para revisión, sin repetir indefinidamente una corrida inviable. El límite de espacio virtual es 7 GiB. Estos límites se aplican al proceso, sin modificar Windows ni la configuración global de WSL.

Crear el archivo `PAUSAR` detiene la cola después del caso actual. Volver a ejecutar la tarea reanuda los casos pendientes. Los casos completos se omiten sólo si coinciden los hashes de código y materiales. Un caso interrumpido se repite desde su comienzo en otro directorio; no se prometió reanudar el campo FDTD a mitad de una corrida. Un cierre de VS Code/WSL o apagado puede interrumpir el proceso.

No se leen créditos de Codex ni se detectan recargas. La cola local puede seguir funcionando sin mensajes del chat, mientras VS Code/WSL permanezcan activos. GitHub recibe los archivos efectivamente comprobados mediante publicaciones explícitas; este programa no contiene tokens ni credenciales.

## Estado científico

La existencia del plan no demuestra finalización. Consultar `estado.json`, `resultado.json` y `proceso.json` por caso. Los intentos fallidos se conservan. Los criterios de estacionariedad y comparación analítica son diagnósticos que deben revisarse junto con la convergencia antes de redactar conclusiones. No se modifica Overleaf en esta fase.
