# Resultados de la campaña a 3 GHz en la tesis

La comparación principal utilizó 5 px/mm. El conjunto de datos se fijó en [la campaña de 61 corridas](https://github.com/JavierMencos/Resultados-de-Tesis/tree/dcbbe9551d1a23f3a738add5e25c5f818cc6d5c8/Tesis_Resultados/Campana_Referencias_20261107): ocho perfiles de onda plana, 41 láminas y doce simulaciones de monopolo. Los datos a precisión completa y sus verificaciones se encuentran en el subdirectorio `analisis` de esa versión.

Los archivos TeX reúnen objetivos, resultados, discusión y anexos numéricos; `figuras` contiene las siete figuras de resultados incluidas en el documento. El registro `compilacion.json` identifica el PDF compilado en VS Code con Ubuntu y la copia fuente descargada de Overleaf mediante sus sumas SHA-256. Las sumas individuales de los archivos TeX se calcularon sobre la copia local; el cotejo con la exportación de Overleaf admitió diferencias entre saltos de línea LF y CRLF.

Para regenerar los cuadros, los anexos y las figuras, instale NumPy y Matplotlib y ejecute desde la raíz de este repositorio:

```bash
python Tesis_Resultados/Tesis_61_corridas/generar_cuadros_figuras.py --campana Tesis_Resultados/Campana_Referencias_20261107 --salida salida_tesis
python Tesis_Resultados/Tesis_61_corridas/graficas_individuales_61.py --campana Tesis_Resultados/Campana_Referencias_20261107 --salida salida_tesis/figuras
```
