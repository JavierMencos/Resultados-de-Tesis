"""Genera una fila por corrida física y compara las mallas que cubrieron el mismo anillo."""
import csv
import json
import math
from pathlib import Path

RAIZ = Path(__file__).resolve().parent


def calcular(m):
    # Convención de normales exteriores en las cuatro caras.
    caras = [-m["interior"], m["exterior"], m["tapa_superior"], m["tapa_inferior"]]
    entrada = -sum(min(0, p) for p in caras)
    salida = sum(max(0, p) for p in caras)
    joule = m["joule"]
    if not all(math.isfinite(p) for p in [*caras, joule]) or entrada <= 0 or joule < 0:
        raise ValueError("Se requieren flujos finitos, entrada positiva y pérdida no negativa.")
    residuo = entrada - salida - joule
    if not math.isclose(residuo, m["residuo"], abs_tol=1e-12*entrada):
        raise ValueError("El residuo del registro difiere del obtenido de las caras.")
    return entrada, salida, joule, residuo


def guardar(nombre, filas):
    if not filas:
        return
    destino = RAIZ / "tablas" / nombre
    destino.parent.mkdir(exist_ok=True)
    with destino.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)


def resumir(ruta):
    corrida = json.loads(ruta.read_text())
    if corrida["prueba"]:
        raise ValueError(f"Se recibió una prueba como corrida física: {ruta.name}")
    a, b = corrida["muestras"]
    if a["dominio_mm"] != b["dominio_mm"] or b["t"] <= a["t"]:
        raise ValueError("Las dos muestras deben cubrir el mismo volumen en orden temporal.")
    ent_a, _, j_a, _ = calcular(a)
    ent, sal, joule, residuo = calcular(b)
    terminos = ["interior", "exterior", "tapa_superior", "tapa_inferior", "joule"]
    return dict(archivo=ruta.name, medio=corrida["medio"], px_mm=corrida["px_mm"],
                r_min_mm=b["dominio_mm"][0], r_max_mm=b["dominio_mm"][1],
                z_min_mm=b["dominio_mm"][2], z_max_mm=b["dominio_mm"][3],
                t1=a["t"], t2=b["t"], entrada=ent, salida=sal, joule=joule,
                residuo=residuo, disipada_pct=100*joule/ent, saliente_pct=100*sal/ent,
                residuo_pct=100*residuo/ent,
                cambio_temporal_disipada_pp=100*(joule/ent-j_a/ent_a),
                max_cambio_terminos_pct_entrada=100*max(abs(b[k]-a[k]) for k in terminos)/ent,
                segundos=corrida["segundos"], rss_MiB=corrida["rss_max_KiB"]/1024)


def main():
    filas = sorted((resumir(p) for p in (RAIZ/"corridas").glob("*_balance_*.json")),
                   key=lambda f: (f["medio"], f["px_mm"], f["archivo"]))
    guardar("balance_campana.csv", filas)
    pares = []
    for gruesa in filas:
        for fina in filas:
            if fina["medio"] != gruesa["medio"] or fina["px_mm"] <= gruesa["px_mm"]:
                continue
            if any(gruesa[k] != fina[k] for k in ("r_min_mm","r_max_mm","z_min_mm","z_max_mm")):
                raise ValueError("Se intentó comparar anillos diferentes.")
            delta = fina["disipada_pct"] - gruesa["disipada_pct"]
            pares.append(dict(corrida_gruesa=gruesa["archivo"], corrida_fina=fina["archivo"],
                         cambio_disipada_pp=delta,
                         diferencia_rel_pct_ref_fina=100*abs(delta)/fina["disipada_pct"] if fina["disipada_pct"] else "",
                         cambio_residuo_pp=fina["residuo_pct"]-gruesa["residuo_pct"],
                         factor_tiempo=fina["segundos"]/gruesa["segundos"],
                         factor_memoria=fina["rss_MiB"]/gruesa["rss_MiB"]))
    guardar("balance_refinamiento.csv", pares)
    print(f"Corridas físicas: {len(filas)}. Comparaciones de malla: {len(pares)}.")


if __name__ == "__main__":
    main()
