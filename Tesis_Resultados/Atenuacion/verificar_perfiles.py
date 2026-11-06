"""Reejecuta sólo el posprocesamiento histórico para los cinco perfiles exportados."""
import argparse
import contextlib
import csv
import io
from pathlib import Path

import numpy as np
from scipy import stats as scipy_stats
from scipy.optimize import curve_fit

root = Path(__file__).resolve().parent
source = (root / "simulador_original.py").read_text(encoding="utf-8")
# Se usa únicamente la sección de ajuste del código auditado. Se omiten Meep y la exportación.
bloque = source[source.index("limite_inf = 2.0"):source.index("# 6. EXPORTACIÓN")]
parser = argparse.ArgumentParser()
parser.add_argument("--todos-los-bloques", action="store_true", help="Incluye la última posición posible de inicio del bloque")
corregido = parser.parse_args().todos_los_bloques
if corregido:
    assert bloque.count("max(1, n - block_len)") == 1
    bloque = bloque.replace("max(1, n - block_len)", "max(1, n - block_len + 1)")
destino = root / "tablas"
historico = list(csv.DictReader((destino / "atenuacion.csv").open(encoding="utf-8")))
salida = []
for fila in historico:
    ruta = root.parent / fila["fuente"]
    if not ruta.is_file():
        continue
    datos = np.loadtxt(io.StringIO("\n".join(x for x in ruta.read_text().splitlines()
        if x and not x.startswith(("#", "Radio_mm")))), delimiter=",")
    r, s_abs, db = datos.T
    np.testing.assert_allclose(db, 10*np.log10(s_abs*(r*r+1e-9)+1e-20), atol=1e-9)
    # El original exportó linspace(0, R_max, n), con R_max = 5*lambda_medio.
    ns = dict(np=np, scipy_stats=scipy_stats, curve_fit=curve_fit, r_coords=r,
              R_max=r[-1], lambda_medio=r[-1]/5, intensidad_db=db,
              tan_delta_actual=float(ruta.read_text().split("tan_delta=")[1].split()[0]),
              alpha_teorico_dB_mm=float(fila["teoria_dB_mm"]))
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(bloque, "ajuste_original", "exec"), ns)
    lo, hi = ns["ci_boot"]
    esperado = (fila["modelo"], round(float(fila["alpha_dB_mm"]),4),
                float(fila["IC95_inf"]), float(fila["IC95_sup"]))
    obtenido = (ns["nombre_modelo"], round(float(ns["alfa_real"]),4), round(lo,4), round(hi,4))
    salida.append(dict(perfil=ruta.name, n_ajuste=len(ns["r_seguro"]), modelo=obtenido[0],
                       alpha=obtenido[1], IC95_inf=obtenido[2], IC95_sup=obtenido[3],
                       coincide_a_4_decimales=obtenido==esperado))
    print(salida[-1],flush=True)
archivo = "sensibilidad_bootstrap.csv" if corregido else "auditoria_perfiles.csv"
with (destino/archivo).open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=salida[0]); w.writeheader(); w.writerows(salida)

