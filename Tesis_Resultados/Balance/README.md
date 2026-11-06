# Balance energético local

Cada JSON de corridas/ identificó medio, resolución, fecha UTC (en el nombre), versión de Meep, sistema, tiempo de ejecución, RSS máxima del proceso, región y dos mediciones temporales. Las potencias se expresaron en unidades de Meep. El paquete empleó la fuente y los parámetros del simulador de atenuación. El anillo se situó entre una y dos longitudes de onda en radio y entre 0.25 y 1.25 longitudes de onda en altura. Para un mismo medio los límites se conservaron en mm al refinar la malla. Al cambiar de medio se conservó la definición en longitudes de onda y cambió el volumen físico.

## Campaña terminada el 6 de noviembre de 2026

| Identificador | Medio | Resolución (px/mm) | Joule/entrada (%) | Salida/entrada (%) | Residuo/entrada (%) | Tiempo (s) | RSS (MiB) |
|---|---|---:|---:|---:|---:|---:|---:|
| B-VA05 | Vacío | 5 | 0.0000 | 99.9861 | 0.013943 | 26977.1 | 4868.2 |
| B-CO05 | Concreto | 5 | 30.3782 | 69.6198 | 0.002011 | 6491.7 | 1326.1 |
| B-AS05 | Agua salada | 5 | 81.1695 | 18.7757 | 0.054794 | 157.3 | 178.6 |
| B-TM05 | Tejido muscular | 5 | 74.5328 | 25.4343 | 0.032973 | 300.3 | 213.2 |
| B-AS10 | Agua salada | 10 | 80.8316 | 19.1468 | 0.021640 | 1581.1 | 384.3 |

Se informaron las segundas muestras. [Índice y hashes](tablas/indice_corridas.csv) vinculó cada identificador con su JSON. [Cuadro completo](tablas/balance_campana.csv) incluyó tiempos, dominios y variaciones temporales. Cada JSON tuvo además un CSV homónimo en tablas/ con las dos muestras y los términos por cara.

En agua salada, el refinamiento de 5 a 10 px/mm redujo la fracción disipada en 0.337943 puntos porcentuales, equivalente al 0.418083 % de la fracción de la malla fina. La entrada absoluta bajó un 29.895750 % y Joule un 30.187624 % respecto de la malla gruesa. La comparación cuantificó la sensibilidad de la fracción normalizada, mientras que las potencias absolutas conservaron una fuerte dependencia de malla. Dos resoluciones resultaron insuficientes para obtener un orden de convergencia del balance o una extrapolación fiable al continuo.

La máxima variación de cualquiera de las cuatro potencias de cara o Joule entre muestras, normalizada por la entrada final, fue de 0.017448 % en vacío. Su residuo pasó de 0.000308 % a 0.013943 %. En los medios con pérdidas las variaciones de los términos fueron menores que 0.000144 %. La separación temporal de aproximadamente un período proporcionó una comprobación limitada del régimen alcanzado. El residuo pudo incluir transitorios, discretización e integración. Los valores publicados carecieron de una estimación estadística de incertidumbre del balance. Los IC de atenuación, las discrepancias teóricas, la variación temporal y las diferencias de malla se conservaron como diagnósticos separados.

Con las normales orientadas hacia fuera, los flujos se obtuvieron de los campos complejos sincronizados. En el archivo de origen, interior se guardó positivo hacia dentro y los otros flujos de superficie, positivos hacia fuera. Primero se transformaron las cuatro caras a normales salientes y después se agruparon por signo. La entrada y la salida son sumas de flujos netos por cara. La disipación se integró independientemente sobre el volumen. Se usó R = entrada − salida − Joule; en el cuadro comparativo se expresó 100 R / entrada total. El campo residuo_relativo del JSON empleó el flujo de la pared interior como denominador. Las fracciones se refieren sólo al anillo. El cambio entre las dos muestras registra estabilidad temporal; la sensibilidad de malla se calcula con dos resoluciones.

En Ubuntu con el entorno Python de Meep y NumPy 2, ejecutar desde esta carpeta:

    python balance.py agua_salada --resolucion 10
    python resumir_balance.py corridas/NOMBRE_DE_LA_CORRIDA.json
    python comparar_balances.py

También se archivó [.vscode/tasks.json](.vscode/tasks.json). Para usarlo se abrió esta carpeta en VS Code conectado a Ubuntu y se seleccionó la tarea de cada medio. La variable TESIS_PYTHON debió apuntar al intérprete del entorno de Meep. La tarea compuesta reprodujo las cuatro corridas adicionales en secuencia.

La primera instrucción simula; cada ejecución crea un archivo nuevo. Las siguientes sólo procesan los registros. Las corridas físicas usan la duración de estabilización del simulador y una segunda lectura aproximadamente un período después. En pruebas/ se archivaron los ensayos de instrumentación. Para reproducir la campaña se usó un hilo OpenMP y un hilo OpenBLAS. El equipo fue un AMD Ryzen 5 4600H con WSL2 y Ubuntu. Los encabezados de los CSV identifican unidades y normalización. La salida balance_refinamiento.csv se genera cuando hay dos mallas de un mismo medio.

## Entorno y costo medido

Se utilizó Ubuntu 24.04.4 LTS, Python 3.13.13, NumPy 2.4.3, SciPy 1.17.1 y Meep 1.33.0-beta. WSL informó 7 806 152 KiB de memoria total, equivalentes a 7.44 GiB. Cada proceso de Meep empleó un hilo OpenMP y uno OpenBLAS. Las cuatro corridas adicionales se iniciaron mediante tareas de VS Code y se ejecutaron secuencialmente. El tiempo de pared incluyó inicialización, pasos temporales, extracción e integración. La RSS máxima correspondió al proceso, no al consumo total del equipo. Los factores observados de tiempo y memoria de agua salada fueron 10.052 y 2.152 al duplicarse la resolución. Se trataron como costos de estas ejecuciones, cuya comparación pudo estar afectada por la actividad del sistema.

El código de simulación tuvo SHA-256 9d3705dfe23465a707f0ecf3964179facfab07f8655503fc2e5bcb26cedf793e. Los hashes restantes se reunieron en SHA256SUMS. La auditoría histórica de atenuación y las pruebas cortas tuvieron archivos y propósitos separados.

La sincronización temporal siguió la [documentación de Meep](https://meep.readthedocs.io/en/latest/Synchronizing_the_Magnetic_and_Electric_Fields/). La cuadratura explícita incluyó el factor cilíndrico 2πr, de acuerdo con su [convención de integración](https://meep.readthedocs.io/en/latest/Exploiting_Symmetry/).
