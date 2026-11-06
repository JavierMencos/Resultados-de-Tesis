# Resultados de las simulaciones FDTD a 3 GHz

| Serie | Contenido | Localización |
|---|---|---|
| Atenuación histórica | Diez configuraciones. Vacío 5, concreto 5 y 10, agua salada 5, 10, 20 y 40, tejido muscular 5, 10 y 20 px/mm. Los perfiles y figuras originales se conservaron en esta carpeta. | [Índice de ajustes, IC y fuentes](Atenuacion/tablas/atenuacion.csv) |
| Verificación de la atenuación | Reajuste de los cinco perfiles numéricos archivados y comprobación de ambos límites del intervalo de confianza. | [Auditoría](Atenuacion/tablas/auditoria_perfiles.csv) |
| Balance energético | Nuevas integraciones de flujo superficial y pérdida de Joule en el mismo volumen. | [Guía de reproducción](Balance/README.md) · [Registros de corrida](Balance/corridas/) · [Cuadro de resultados](Balance/tablas/balance_campana.csv) |
| Pruebas técnicas | Dos arranques cortos en agua salada a 5 px/mm, excluidos del análisis físico. | [Pruebas](Balance/pruebas/) |
| Compilación LaTeX local | PDF final, fuentes actualizadas, registros de los intentos y hashes del código fuente. | [Archivo de compilaciones](LaTeX/README.md) |

En los nombres, 5px indicó 5 px/mm. Los archivos de perfil sin extensión fueron CSV de texto. El identificador de fuente del cuadro de atenuación corresponde al nombre del perfil o al commit de la figura que contiene el informe estadístico. Los porcentajes de discrepancia con la teoría, los IC del ajuste y los cambios al refinar la malla se documentaron por separado. Las versiones de referencia fueron [datos de atenuación](https://github.com/JavierMencos/Resultados-de-Tesis/tree/e96d8776842d98bcb3e97faac9887df156888eac/Tesis_Resultados) y [simulador original](https://github.com/JavierMencos/Resultados-de-Tesis/blob/0dc64c175678ffb762755169c651f998836e8f8a/Tesis_programa.py).
