"""Verifica una corrida física y resume ambas muestras. Uso: python3 resumir_balance.py ruta.json"""
import argparse
import csv
import json
import math
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("archivo", type=Path)
args = parser.parse_args()
registro = json.loads(args.archivo.read_text(encoding="utf-8"))
if registro["prueba"] or len(registro["muestras"]) != 2:
    parser.error("Se requiere una corrida física con dos muestras.")
inicial, final = registro["muestras"]
terminos = ["interior", "exterior", "tapa_superior", "tapa_inferior", "joule"]
if final["t"] <= inicial["t"] or final["dominio_mm"] != inicial["dominio_mm"]:
    raise ValueError("Las muestras no corresponden a la misma región en tiempos sucesivos.")
for m in (inicial, final):
    if not all(math.isfinite(m[k]) for k in terminos) or m["interior"] <= 0:
        raise ValueError("Muestra no válida para la normalización por la cara interior.")
    residuo = m["interior"] - sum(m[k] for k in terminos[1:])
    if not math.isclose(residuo, m["residuo"], abs_tol=1e-12*abs(m["interior"])):
        raise ValueError("El residuo registrado no coincide con las potencias.")
    if not math.isclose(residuo/m["interior"], m["residuo_relativo"], abs_tol=1e-12):
        raise ValueError("El residuo relativo no coincide con la normalización.")

salida = Path(__file__).resolve().parent / "tablas" / (args.archivo.stem + ".csv")
salida.parent.mkdir(exist_ok=True)
with salida.open("w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["termino", "muestra_1_Meep", "muestra_2_Meep", "porcentaje_de_interior_final",
                "cambio_pct_de_interior_final", "cambio_pct_del_termino_inicial"])
    for k in terminos + ["residuo"]:
        cambio = final[k] - inicial[k]
        w.writerow([k, inicial[k], final[k], 100*final[k]/final["interior"],
                    100*cambio/final["interior"], 100*cambio/abs(inicial[k]) if inicial[k] else ""])
print(salida)

# Con las normales hacia fuera, un término negativo identifica una cara de entrada.
# Esta suma clasifica los flujos netos de cada cara, no separa ondas incidentes y reflejadas.
for m in (inicial, final):
    caras = [-m["interior"], m["exterior"], m["tapa_superior"], m["tapa_inferior"]]
    entra = -sum(min(p, 0) for p in caras)
    sale = sum(max(p, 0) for p in caras)
    print(f't={m["t"]:.3f}: entrada={entra:.9g}, salida={sale:.9g}, '
          f'Joule/entrada={100*m["joule"]/entra:.6f} %, '
          f'residuo/entrada={100*m["residuo"]/entra:.6f} %')
