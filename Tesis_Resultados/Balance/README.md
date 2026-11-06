# Balance energético local

Cada JSON de corridas/ identificó medio, resolución, fecha UTC (en el nombre), versión de Meep, sistema, tiempo de ejecución, RSS máxima del proceso, región y dos mediciones temporales. Las potencias se expresaron en unidades de Meep. El paquete empleó la fuente y los parámetros del simulador de atenuación. El anillo se situó entre una y dos longitudes de onda en radio y entre 0.25 y 1.25 longitudes de onda en altura. Para un mismo medio los límites se conservaron en mm al refinar la malla. Al cambiar de medio se conservó la definición en longitudes de onda y cambió el volumen físico.

Con las normales orientadas hacia fuera, los flujos se obtuvieron de los campos complejos sincronizados. En el archivo de origen, interior se guardó positivo hacia dentro y los otros flujos de superficie, positivos hacia fuera. Primero se transformaron las cuatro caras a normales salientes y después se agruparon por signo. La entrada y la salida son sumas de flujos netos por cara. La disipación se integró independientemente sobre el volumen. Se usó R = entrada − salida − Joule; en el cuadro comparativo se expresó 100 R / entrada total. El campo residuo_relativo del JSON empleó el flujo de la pared interior como denominador. Las fracciones se refieren sólo al anillo. El cambio entre las dos muestras registra estabilidad temporal; la sensibilidad de malla se calcula con dos resoluciones.

En Ubuntu con el entorno Python de Meep y NumPy 2, ejecutar desde esta carpeta:

    python balance.py agua_salada --resolucion 10
    python resumir_balance.py corridas/NOMBRE_DE_LA_CORRIDA.json
    python comparar_balances.py

La primera instrucción simula; cada ejecución crea un archivo nuevo. Las siguientes sólo procesan los registros. Las corridas físicas usan la duración de estabilización del simulador y una segunda lectura aproximadamente un período después. En pruebas/ se archivaron los ensayos de instrumentación. Para reproducir la campaña se usó un hilo OpenMP y un hilo OpenBLAS. El equipo fue un AMD Ryzen 5 4600H con WSL2 y Ubuntu. Los encabezados de los CSV identifican unidades y normalización. La salida balance_refinamiento.csv se genera cuando hay dos mallas de un mismo medio.
