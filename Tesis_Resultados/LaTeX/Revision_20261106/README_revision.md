# Revisión de unidades, alcance y conclusiones — 6 de noviembre de 2026

Esta revisión sustituyó la metodología que no describía la campaña ejecutada y el contenido de plantilla sobre un péndulo en conclusiones y recomendaciones. Conservó las cifras, los intervalos, las ecuaciones de resultados y las figuras históricas. No ejecutó nuevas simulaciones Meep.

## Identificadores

| ID | Medio | Resolución |
|---|---|---|
| B-AS05 | Agua salada | 5 px/mm |
| B-VA05 | Vacío | 5 px/mm |
| B-CO05 | Concreto | 5 px/mm |
| B-TM05 | Tejido muscular | 5 px/mm |
| B-AS10 | Agua salada | 10 px/mm |

B identificó un balance energético. AS, VA, CO y TM identificaron el medio; 05 y 10 identificaron la resolución. El anillo de cada medio se definió con su longitud de onda, por lo que no se compararon volúmenes físicos idénticos entre materiales.

## Unidades

Se documentaron a=1 mm, x_SI=a x_M, t_SI=(a/c)t_M y f_M=f_SI a/c. Una unidad temporal correspondió a 3.33564 ps. Las potencias se expresaron normalizadas por P_*=E_*² a²/Z0, con la escala de campo E_* sin calibrar. Los cocientes y porcentajes fueron adimensionales. Los segundos de ejecución representaron tiempo de pared. El apartado 7.5 incluyó la conversión de conductividad utilizada por Meep y las fuentes oficiales.

## Evidencia y límites

La discusión distinguió pérdidas radiales relativas en medios homogéneos, disipación en el anillo, transporte saliente y cierre del balance. Se mantuvieron separadas la incertidumbre condicional del ajuste, la discrepancia teórica, la sensibilidad de malla y el residuo energético.

Se evaluaron expresamente los tres objetivos específicos. El protocolo quedó propuesto y documentado. La predicción de pérdidas a través de interfaces y la validación de un modelo de propagación con datos independientes quedaron pendientes. No se afirmó cumplimiento integral ni validación experimental.

La sensibilidad de la fracción disipada del agua salada fue 0.4181 % respecto de 10 px/mm; las potencias absolutas variaron cerca del 30 %. Un residuo energético inferior a 0.055 % no demostró convergencia espacial. El ajuste en vacío mantuvo su limitación de calidad.

## Compilación y trazabilidad

Se compiló el proyecto desde la tarea de VS Code conectada a Ubuntu/WSL. El registro 20261106T193850Z documentó salida=0, 13.878 s y 117 páginas. Se archivaron el PDF, los seis archivos modificados y los registros JSON y LOG. El JSON guardó hashes de todas las fuentes .tex de primer nivel; SHA256SUMS identificó los archivos de esta revisión. La copia completa del proyecto quedó en Overleaf y en documento/ del espacio de VS Code. Los datos originales y sus figuras permanecieron en las carpetas de atenuación y balance del repositorio.

Se inspeccionaron visualmente metodología, resultados, discusión, conclusiones, recomendaciones y anexos, sin referencias sin resolver en esas páginas. Persistieron avisos ajenos a estas modificaciones: hoja de firmas pendiente, coexistencia de cite y natbib, desbordamientos menores y un carácter matemático no disponible en el marco teórico. La revisión integral de bibliografía y capítulos previos no quedó certificada por esta compilación.
