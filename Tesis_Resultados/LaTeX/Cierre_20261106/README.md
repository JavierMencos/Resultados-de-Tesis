# Tesis revisada: cierre científico y editorial, 6 de noviembre de 2026

Esta es una versión para revisión del asesor, no una tesis declarada aprobada para entrega. Los requisitos científicos y formales pendientes se explican en `ESTADO_DE_CIERRE.md`.

## Contenido
- Todos los capítulos LaTeX, las figuras en `figuras` y los recursos de la plantilla.
- `tesis_revisada.pdf`: compilación local de 106 páginas realizada desde una tarea de VS Code en Ubuntu/WSL.
- `compilacion`: registros de cuatro intentos de esta revisión, incluidos dos fallidos por etiquetas múltiples corregidas. La última compilación, `20261107T010241Z` (UTC), terminó con código 0. Quedaron una advertencia de hoja firmada pendiente y una caja de texto excedida en 2.26 pt; no hubo referencias/citas sin resolver ni glifos ausentes en el registro final.
- `auditoria_referencias.json`: metadatos consultados para corregir autorías, títulos, años y DOI. Las respuestas fallidas se conservaron como tales; no se interpretaron como inexistencia de una referencia.
- `tasks.json`: configuración de tareas del equipo de ejecución. Contiene rutas locales que deben adaptarse al reproducir en otro equipo.

Los datos nuevos de onda plana se publicaron separadamente en `Tesis_Resultados/Verificacion_1D`. Se conservaron las ocho ejecuciones diagnósticas y las ocho de activación suave. Los resultados del monopolo y los balances anteriores permanecieron en sus carpetas históricas.

## Compilación
Abrir el proyecto local en VS Code conectado a Ubuntu y utilizar la tarea de compilación de `compilar_tesis.py`. El script invoca `latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error -outdir=compilacion main.tex` y registra retorno, duración y hashes. Se requieren LaTeX y los paquetes de la plantilla, además de conversión de EPS disponible en el entorno usado.

## Estado de Overleaf
La carga de esta revisión fue rechazada por el control de permisos del navegador. Por tanto, esta carpeta y su PDF constituyen la versión revisada; no se afirmó que Overleaf ya los contuviera. Se preparó un ZIP local completo para su incorporación autorizada posterior. La copia anterior de Overleaf se preservó antes de editar.

La comparación principal siguió siendo a 5 px/mm. La prueba planar verificó la propagación homogénea de forma independiente y no se presentó como convergencia de potencias absolutas del monopolo.
