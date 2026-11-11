"""Posproceso de la campaña a 3 GHz. Uso: python analisis/verificar.py"""
import cmath
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def table(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(value, expected, label):
    if not np.allclose(value, expected, rtol=1e-8, atol=1e-12):
        raise ValueError(f"{label}: {value} frente a {expected}")


def percent(delta, reference):
    return 100 * delta / abs(reference) if reference != 0 else None


def intervals(x, y, block):
    """IC percentil de la pendiente negativa, remuestreo de residuos contiguos."""
    x = x - x.mean()
    projection = x / (x @ x)
    slope = projection @ y
    residual = y - (y.mean() + slope * x)
    rng = np.random.default_rng(0)
    samples = []
    for _ in range(1500):
        starts = rng.integers(0, len(x) - block + 1, size=math.ceil(len(x) / block))
        indices = (starts[:, None] + np.arange(block)).ravel()[:len(x)]
        samples.append(-slope - projection @ residual[indices])
    return np.quantile(samples, [.025, .975])


def reference(r):
    freq = r["frecuencia_Hz"]
    n = cmath.sqrt(r["epsr"] + 1j * r["sigma_eq_S_m"] / (2 * math.pi * freq * r["epsilon0"]))
    k0 = 2 * math.pi * freq / r["c"] / 1000
    alpha = 20 * k0 * n.imag / math.log(10)
    check(alpha, r["alpha_teoria_dB_mm"], r["id"])
    return n, k0, alpha


def profile(r, folder, alpha):
    a = r["ajuste"]
    antenna = r["tipo"] == "antena"
    data = np.genfromtxt(folder / "perfil.csv", names=True, delimiter=",")
    if antenna:
        flux = -.5 * (data["Ez_real"] * data["Hp_real"] + data["Ez_imag"] * data["Hp_imag"])
        check(flux, data["Sr"], r["id"])
        mask = data["usado_ajuste"].astype(bool)
        x = data["r_mm"][mask]
        power = flux[mask] * x**2
    else:
        power = .5 * (data["Ex_real"] * data["Hy_real"] + data["Ex_imag"] * data["Hy_imag"])
        check(power, data["Sz"], r["id"])
        x = data["z_mm"]
    y = 10 * np.log10(power / power[0])
    slope = -np.polyfit(x, y, 1)[0]
    check(slope, a["alpha_dB_mm"], r["id"])
    lo, hi = a["IC95_ajuste_bloques"]
    check(intervals(x, y, a["bloque"]), [lo, hi], r["id"])
    windows = [w["alpha_dB_mm"] for w in r.get("ventanas", [])]
    record = dict(id=r["id"], alpha_dB_mm=slope, teoria_dB_mm=alpha,
                  diferencia_dB_mm=slope-alpha, error_abs_pct=percent(abs(slope-alpha), alpha),
                  IC95_inf=lo, IC95_sup=hi, bloque=a["bloque"], n=len(x), R2=a["R2"],
                  RMSE_dB=a["RMSE_dB"], DW=a["Durbin_Watson"],
                  ventana_min_dB_mm=min(windows) if windows else None,
                  ventana_max_dB_mm=max(windows) if windows else None)
    for factor in (2, 4):
        lower, upper = intervals(x, y, min(len(x), factor*a["bloque"]))
        record.update({f"IC95_inf_Lx{factor}": lower, f"IC95_sup_Lx{factor}": upper})
    return record


def ring(r):
    b = r["balance"][-1]
    faces = np.asarray(b["caras_salientes"])
    pin, pout = -faces[faces < 0].sum(), faces[faces > 0].sum()
    heat = b["joule"]
    residue = (pin - pout - heat) / pin
    check([pin, pout, residue, heat/pin],
          [b["entrada"], b["salida"], b["residuo_rel"], b["fraccion_disipada"]], r["id"])
    return dict(id=r["id"], entrada_M=pin, salida_M=pout, joule_M=heat,
                fraccion_disipada=heat/pin, residuo_pct=100*residue,
                var_temporal_perfil=r["cambio_temporal_perfil"],
                var_temporal_diagnostico=max(r["cambio_temporal"][-2:]))


def slab(r, folder, n, k0):
    d = r["espesor_mm"]
    p = cmath.exp(1j*k0*n*d)
    rho = (1-n)/(1+n)
    denom = 1-rho**2*p**2
    reflect, transmit = abs(rho*(1-p**2)/denom)**2, abs((1-rho**2)*p/denom)**2
    exact = [reflect, transmit, 1-reflect-transmit]
    data = np.genfromtxt(folder/"campos_lamina.csv", delimiter=",", names=True)
    density = .5*r["epsr"]*r["sigma_D_M"]*(data["Ex_real"]**2+data["Ex_imag"]**2)
    absorb = np.trapezoid(density, data["z_mm"])/r["incidente"]
    e,h = np.array([complex(*v) for v in r["campos_monitores_objeto"]]).reshape(2,2)
    inc = r["calibracion"]
    # R necesita la fase compleja del campo incidente, no archivada para este monitor.
    # Se conserva el R calculado en la corrida y se contrasta con la solución analítica.
    t = .5*(e[1]*h[1].conjugate()).real/inc[0]
    measured = np.array([r["R"], t, absorb])
    residual = 1-measured.sum()
    check(measured, [r["R"],r["T"],r["A_integral"]], r["id"])
    check(exact,r["teoria_RTA"],r["id"])
    check(residual,r["residuo_balance"],r["id"])
    result = dict(id=r["id"], reservado=r["validacion_independiente"], espesor_mm=d,
                  residuo_pp=100*residual, perdida_insercion_dB=-10*math.log10(t))
    for key, val, ref in zip("RTA", measured, exact):
        result.update({key:val, key+"_teoria":ref, key+"_error_pp":100*(val-ref)})
    return result


def main():
    plan = load(ROOT/"plan.json")
    state = load(ROOT/"estado.json")
    ids = [job["id"] for job in plan]
    if state["estado"] != "finalizada" or len(set(ids)) != len(ids) or set(ids) != set(state["completadas"]):
        raise ValueError("Plan y estado incompatibles")
    hashes = dict(script_sha256=digest(ROOT/"simular.py"), materiales_sha256=digest(ROOT/"materiales.csv"))
    attempts, index, profiles, rings, slabs = [], [], [], {}, []
    by_case = {}
    for job in plan:
        ident = job["id"]
        accepted = []
        for folder in sorted((ROOT/"corridas"/ident).iterdir()):
            proc = load(folder/"proceso.json") if (folder/"proceso.json").exists() else {}
            exists = (folder/"resultado.json").exists()
            ok = False
            if exists:
                r = load(folder/"resultado.json")
                cfg = load(folder/"configuracion.json")
                ok = (proc.get("retorno")==0 and not proc.get("error") and r["completo"] and r["estacionario"]
                      and all(r[k]==cfg[k]==v for k,v in hashes.items()) and r["id"]==cfg["id"]==ident
                      and (r["tipo"],r["medio"],r["resolucion_px_mm"],r["pml_factor"]) ==
                          (job["tipo"],job["medio"],job["res"],job["pml"]))
                if ok:
                    accepted.append((folder,r))
            attempts.append(dict(id=ident,intento=folder.name,retorno=proc.get("retorno"),
                                 error=proc.get("error"),con_resultado=exists,aceptado=ok))
        if len(accepted)!=1:
            raise ValueError(f"{ident}: {len(accepted)} resultados válidos")
        folder,r = accepted[0]
        n,k0,alpha = reference(r)
        projection = {}
        if r["tipo"] == "lamina":
            slabs.append(slab(r,folder,n,k0))
        else:
            projection = profile(r,folder,alpha)
            profiles.append(projection)
        if r["tipo"] == "antena":
            rings[ident]=ring(r)
            by_case[ident] = dict(alpha_dB_mm=projection["alpha_dB_mm"],
                                  **{k:rings[ident][k] for k in ("entrada_M","salida_M","joule_M","fraccion_disipada","residuo_pct")})
        index.append(dict(id=ident,tipo=r["tipo"],medio=r["medio"],px_mm=job["res"],pml_lambda=job["pml"],
                          intento=folder.name,estacionario=r["estacionario"],segundos=r["segundos"],
                          rss_max_KiB=r["rss_max_KiB"],lambda_mm=r["lambda_mm"],celdas_por_lambda=job["res"]*r["lambda_mm"],
                          registro=(folder/"resultado.json").relative_to(ROOT).as_posix()))
    table(ROOT/"indice_corridas.csv", index)
    table(OUT/"atenuacion.csv",profiles)
    table(OUT/"balance_anular.csv",list(rings.values()))
    table(OUT/"laminas.csv",slabs)
    pairs = []
    def compare(kind, a, b):
        for key,left in by_case[a].items():
            right = by_case[b][key]
            pairs.append(dict(estudio=kind,caso=a,referencia=b,magnitud=key,valor=left,
                              valor_ref=right,diferencia=left-right,diferencia_rel_pct=percent(left-right,right)))
    for medium in ("agua_salada","tejido_muscular","concreto"):
        group = sorted([j for j in plan if j["tipo"]=="antena" and j["medio"]==medium and j["pml"]==2],
                       key=lambda j:j["res"])
        for i,a in enumerate(group):
            for b in group[i+1:]:
                compare("malla",a["id"],b["id"])
        compare("PML",group[0]["id"],group[0]["id"]+"_pml3")
    table(OUT/"sensibilidad.csv",pairs)
    orders = []
    for key in by_case["antena_agua_salada_5px"]:
        q5,q10,q15,q20 = [by_case[f"antena_agua_salada_{n}px"][key] for n in (5,10,15,20)]
        ratio = (q5-q10)/(q10-q20) if q10!=q20 else math.nan
        order = math.log2(ratio) if ratio>1 else None
        limit = q20+(q20-q10)/(ratio-1) if order else None
        prediction = limit+(q20-limit)*(20/15)**order if order else None
        orders.append(dict(magnitud=key,q5=q5,q10=q10,q15=q15,q20=q20,
                           monotona_4=bool((q5<q10<q15<q20) or (q5>q10>q15>q20)),
                           orden_aparente_5_10_20=order,limite_condicional=limit,
                           estimacion_menos_q20=(limit-q20) if order else None,
                           prediccion_menos_q15=(prediction-q15) if order else None))
    table(OUT/"refinamiento_agua.csv",orders)
    (ROOT/"intentos.json").write_text(json.dumps(attempts,indent=2)+"\n",encoding="utf-8")
    meta=dict(fecha_fin_UTC=state["fin_turno_UTC"],casos=len(index),intentos=len(attempts),
              intentos_sin_resultado=sum(not a["con_resultado"] for a in attempts),**hashes)
    (ROOT/"PUBLICACION.json").write_text(json.dumps(meta,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
