# Auditoría de materiales a 3 GHz — 7 de noviembre de 2026

Se contrastaron los parámetros del programa histórico con fuentes identificables. **No se encontró respaldo exacto a 3 GHz para los tres pares materiales históricos.** Esto no invalida su verificación numérica como medios idealizados, pero impide presentarlos como propiedades medidas y trazables de muestras reales.

| Medio | Programa: εr; σ [S/m] | Referencia calculada: εr; σ equivalente [S/m] | Procedencia |
|---|---|---|---|
| Vacío | 1; 0 | 1; 0 | Definición del vacío ideal |
| Concreto | 4.5; 0.05 | 5.24; 0.109105 | UIT-R P.2040-4, cuadro 3, rama 1–100 GHz |
| Agua salada | 78; 4 | 70.314033; 6.372112 | UIT-R P.527-6, 3 GHz, 20 °C y 35 g/kg |
| Músculo | 52.7; 2.2 | 52.057998; 2.142140 | IT’IS V5.0, Muscle, modelo Gabriel |

Los valores calculados son evaluaciones deterministas de modelos publicados, no mediciones propias, intervalos de confianza ni valores universales. Las condiciones de agua fueron elegidas para el contraste; no se recuperaron del programa original.

## Fuentes reales y condiciones

- **IT’IS Foundation (2025), Tissue Properties Database V5.0**, DOI [10.13099/VIP21000-05-0](https://doi.org/10.13099/VIP21000-05-0). Se utilizó la tabla dieléctrica principal basada en Gabriel, no la tabla alternativa. Se evaluó el modelo Cole–Cole de cuatro términos a 3 GHz. El JSON conservó los coeficientes y los hashes del ZIP y del archivo de datos. [Descripción del modelo](https://itis.swiss/virtual-population/tissue-properties/database/dielectric-properties). No se infirió una incertidumbre del material a partir de estadísticas de densidad o propiedades térmicas de esa base.
- **UIT-R P.2040-4 (2025)**, [documento oficial](https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.2040-4-202509-I!!PDF-E.pdf). Se evaluó εr=5.24 y σ=0.0462 f_GHz^0.7822. Se trató de un modelo de clase de material; no de una caracterización del concreto particular de la tesis.
- **UIT-R P.527-6 (2021)**, [documento oficial](https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.527-6-202109-I!!PDF-E.pdf), §5.1.2, ecuaciones 14–27 y auxiliares 8–13. A 20 °C y 35 g/kg, la conductividad iónica resultó 4.79126 S/m. La conductividad equivalente a 3 GHz incluyó además la relajación dieléctrica: σ_eq=2πf ε0 εr''. Se conservó el factor aproximado 18 de la ecuación 16, sin sustituirlo por una constante más precisa. No deben añadirse nuevamente esas pérdidas a un modelo que ya las incluya.

## Qué ocurrió con las citas suministradas

| Clave | Hallazgo | Uso admisible |
|---|---|---|
| gedney2020 | El libro de Gedney se publicó originalmente en 2011; la ficha suministrada no coincidió con esa fecha. [Editorial](https://link.springer.com/book/10.1007/978-3-031-01712-4). | Método FDTD; vacío como definición física. |
| fichte2021 | El título correspondió a Dinh et al., Construction and Building Materials 311, 125234. [DOI](https://doi.org/10.1016/j.conbuildmat.2021.125234). | Dependencia con humedad y porosidad; no se verificó el par 4.5/0.05 a 3 GHz en el texto accesible. |
| hossain2026 | El título se localizó con DOI 10.3390/ndt4010011, NDT 4(1), 11; los metadatos no coincidieron con Hossain/Sensors. [Artículo](https://www.mdpi.com/2813-477X/4/1/11). | No se utilizó para atribuir 52.7/2.2. |
| ieee2021 | La ficha mezcló identificadores y alcance. La norma conjunta identificada fue IEC/IEEE 62209-1528:2020. [IEEE](https://standards.ieee.org/ieee/62209-1528/7325/). | Procedimientos SAR; no se verificó una tabla que respaldara el par de músculo. |
| martinez2022 | No se verificó el artículo con el título y metadatos proporcionados. | No se empleó como procedencia de 70/4 ni de 78/4. |
| kim2025 | No se verificó el artículo con el título y metadatos proporcionados. | No se empleó como procedencia de 4.5/0.05. |

La ausencia de una coincidencia en esta búsqueda no demostró que una publicación no existiera. Las consultas y candidatos de Crossref quedaron en `metadatos_consultados.json`.

## Reproducción y significado de las diferencias

Ejecutar `python3 parametros_referencia.py`. No requiere paquetes externos. La primera ejecución descarga datos IT’IS; las posteriores usan `cache/Database-V5-0.zip`. En VS Code/WSL se ejecutó la tarea **Tesis: auditar materiales**. Se comprobó el límite de salinidad cero contra la expresión de agua pura, la pasividad y la atenuación nula del vacío. Un primer intento falló al leer Latin-1 como UTF-8; se corrigió el lector antes de producir los resultados finales.

El CSV comparó las predicciones analíticas de ambos conjuntos con las mismas constantes SI. La atenuación teórica cambió +101.94 % en concreto, +64.14 % en agua y −2.01 % en músculo. **Son cambios de modelo material, no errores de discretización ni incertidumbres estadísticas.** Los números originales de la tesis conservaron las constantes ligeramente redondeadas de su programa y no se sustituyeron por los de este contraste.

`auditar_materiales.py` reprodujo la consulta bibliográfica y la comparación teórica 70 frente a 78 manteniendo σ=4 S/m. Esta última elevó α de 0.73262055 a 0.77131043 dB/mm (+5.281 %). La columna que compara la pendiente histórica con εr=70 es únicamente un diagnóstico contrafactual: no representa una simulación ejecutada con ese parámetro.

## Estado y trabajo necesario para cerrar el alcance

Las corridas históricas, los cinco balances locales y la verificación planar quedaron terminados para sus parámetros nominales. No se justificó repetirlos para corregir una cita. Para afirmar predicción cuantitativa de materiales reales a 3 GHz, deberá fijarse un conjunto trazable y realizarse una campaña adicional claramente separada. Una referencia publicada no valida por sí sola una muestra real.

Para cubrir transmisión por penetración a través de una pared/interfaz y capacidad predictiva independiente, sigue siendo pertinente una prueba vacío–lámina–vacío: separación de flujos incidente/reflejado/transmitido, absorción volumétrica independiente, comparación con solución de lámina, refinamiento espacial y temporal, y espesores reservados para comprobación. No se atribuyeron estos resultados aún no ejecutados a la tesis.

No se inició ninguna nueva corrida FDTD larga en esta auditoría. Los resultados históricos permanecieron disponibles e identificados.
