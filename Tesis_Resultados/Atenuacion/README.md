# Atenuación y auditoría de incertidumbres

La carpeta tablas/ reunió los resultados históricos de diez configuraciones, las diferencias de malla y las dos auditorías del remuestreo. El origen de cada fila se conservó en atenuacion.csv. Los cinco perfiles CSV sin extensión se ubicaron en la carpeta superior Tesis_Resultados. Los cinco informes de figuras se conservaron en informes/.

Desde esta carpeta de una copia completa del repositorio, se reprodujeron los cuadros mediante

    python analisis.py
    python verificar_perfiles.py
    python verificar_perfiles.py --todos-los-bloques

El primer programa usó la biblioteca estándar. Los otros requirieron NumPy y SciPy, y ejecutaron únicamente el ajuste del simulador_original.py archivado. La opción --todos-los-bloques incluyó la última posición válida de inicio de un bloque en el remuestreo. Su resultado se guardó en sensibilidad_bootstrap.csv. Los archivos de auditoría permitieron distinguir los IC originales de esa comprobación corregida. En vacío cambió el extremo superior de 0.0075 a 0.0074 dB/mm. En los otros cuatro perfiles coincidió a cuatro decimales.

Las cinco configuraciones respaldadas sólo por figuras mantuvieron sus IC originales. La tabla atenuacion.csv conservó el registro histórico para facilitar la trazabilidad. La calidad del ajuste de vacío se marcó como insuficiente. Los IC describieron la incertidumbre condicional del ajuste. La discrepancia con la teoría y la sensibilidad a la malla se informaron por separado.
