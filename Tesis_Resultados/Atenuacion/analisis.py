"""Reproduce los cuadros de atenuación con la biblioteca estándar de Python."""
import csv
import re
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATOS = ROOT.parent
OUT = ROOT / "tablas"
OUT.mkdir(exist_ok=True)
# Cada commit corresponde a la última versión publicada de esa figura.
REPORTES = {"agua_salada": {5:"823defa",10:"adbe296",20:"100e2a0"},
            "concreto": {5:"209d7d6"}, "tejido_muscular": {5:"e96d877"}}

def valor(patron, texto):
    match = re.search(patron, texto)
    if not match:
        raise ValueError(f"Campo ausente: {patron}")
    return match.groups()

def guardar(nombre, filas):
    with (OUT/nombre).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=filas[0].keys())
        writer.writeheader()
        writer.writerows(filas)

def extraer(medio, res, fuente, texto):
    a, = valor(r"alpha_(?:app=|\{app\}=)([\d.]+)", texto)
    t, = valor(r"alpha_teorico=([\d.]+)", texto)
    bloque, lo, hi = valor(r"(?:CI 95% bootstrap \(block_len=|bootstrap por bloques, block_len=)(\d+)\):\s*\[([\d.]+),\s*([\d.]+)\]", texto)
    modelo, = valor(r"(?:Modelo Evaluado: |Delta-AIC>10.0\): )(M\d)",texto)
    rmse, dw = valor(r"RMSE[=:]\s*([\d.]+) dB\s*\| DW[=:]\s*([\d.]+)",texto)
    r2, = valor(r"R(?:\^2|²)[=:]\s*([-\d.]+)", texto)
    apto, = valor(r"Ajuste utilizable[^:\n]*:\s*(INVÁLIDO|VÁLIDO)", texto)
    a,t = float(a),float(t)
    pct = re.search(r"diferencia ([-\d.]+)%", texto)
    return dict(medio=medio, px_mm=res, h_mm=1/res, modelo=modelo, alpha_dB_mm=a,
        IC95_inf=lo, IC95_sup=hi, bloque=bloque, teoria_dB_mm=t,
        error_abs_dB_mm=round(abs(a-t),6),
        error_pct=abs(float(pct[1])) if pct else (round(100*abs(a-t)/t,3) if t else ""),
        R2=r2, RMSE_dB=rmse,DW=dw,apto=apto=="VÁLIDO",
        fuente=fuente)

filas=[]
for f in sorted(DATOS.glob("Resultados_*px")):
    medio,res=valor(r"Resultados_(.+?)(\d+)px$", f.name)
    contenido=f.read_text(encoding="utf-8-sig")
    assert f"resolution={res} px/mm" in contenido
    filas.append(extraer(medio,int(res),f.name,contenido))
for medio, corridas in REPORTES.items():
    for res, commit in corridas.items():
        filas.append(extraer(medio,res,commit,(ROOT/"informes"/f"{commit}.txt").read_text(encoding="utf-8-sig")))
filas.sort(key=lambda f:(f["medio"],f["px_mm"]))
guardar("atenuacion.csv",filas)
comparaciones=[]
for medio in sorted({f["medio"] for f in filas}):
    serie=[f for f in filas if f["medio"]==medio]
    fino=serie[-1]
    for f in serie[:-1]:
        comparaciones.append(dict(medio=medio,px_mm=f["px_mm"],ref_px_mm=fino["px_mm"],
            diferencia_pct=round(100*abs(f["alpha_dB_mm"]/fino["alpha_dB_mm"]-1),4)))
guardar("sensibilidad.csv",comparaciones)
agua=[f for f in filas if f["medio"]=="agua_salada"]
ordenes=[]
for x,y,z in zip(agua,agua[1:],agua[2:]):
    assert y["px_mm"]==2*x["px_mm"] and z["px_mm"]==2*y["px_mm"]
    a,b,c=[f["alpha_dB_mm"] for f in (x,y,z)]
    ordenes.append(dict(mallas=f'{x["px_mm"]}/{y["px_mm"]}/{z["px_mm"]}',
                        orden_aparente=math.log2(abs((b-a)/(c-b)))))
guardar("orden_agua.csv",ordenes)
print(f"{len(filas)} configuraciones procesadas en {OUT}")

