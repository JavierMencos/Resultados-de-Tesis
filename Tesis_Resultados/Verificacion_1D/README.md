# Verificación de propagación homogénea 1D

VP = verificación planar; VA vacío, CO concreto, AS agua salada, TM tejido muscular. 05/10 = px/mm.
No es una corrida de antena ni un balance cilíndrico. Fuente no calibrada en SI.

`diagnostico_inicial`: ocho corridas con fuente abrupta; el vacío no cumplió estabilidad temporal. Se conservan por trazabilidad.
`suave`: ocho corridas con encendido width=2T, slowness=6. Sus campos, ajustes, IC y metadatos se resumieron en `resumen.csv`.
Ambas versiones se ejecutaron en VS Code/Ubuntu, secuencialmente y con un hilo. Código y resultados no se mezclan.

Reproducción: ejecutar `verificar_onda_plana.py` en el entorno Meep de la tesis mediante la tarea de VS Code incluida. Cada ejecución genera nombres UTC nuevos. `integrar_verificacion.py` conserva el procedimiento de análisis y generación de la figura; requiere adaptar la raíz del documento al lugar de descarga.
Los IC son condicionales al perfil determinista. No incluyen incertidumbre de parámetros materiales, frontera, tiempo ni discretización.
El control temporal usa dos instantes separados por T, y no garantiza ausencia de oscilaciones más lentas.
Con activación suave: suma de tiempos 17.911 s; máximo RSS acumulativo 111.195 MiB.
La reducción de error frente a la teoría respalda esta configuración planar; no certifica convergencia de amplitudes del monopolo.
