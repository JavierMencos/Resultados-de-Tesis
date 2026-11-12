"""Regenera cuatro perfiles del monopolo desde la campaña archivada.

Uso: python graficas_individuales_61.py --campana RUTA --salida RUTA
No ejecuta Meep. Conserva las pendientes e intervalos del análisis archivado.
"""
import argparse
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--campana", type=Path, required=True)
p.add_argument("--salida", type=Path, required=True)
a = p.parse_args()
a.salida.mkdir(parents=True, exist_ok=True)

def rows(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

index = {r["id"]: r for r in rows(a.campana / "indice_corridas.csv")}
analysis = {r["id"]: r for r in rows(a.campana / "analisis/atenuacion.csv")}
materials = {r["medio"]: r for r in rows(a.campana / "materiales.csv")}
media = [("vacio", "Vacío", "VA"), ("concreto", "Concreto", "CO"),
         ("agua_salada", "Agua marina", "AS"), ("tejido_muscular", "Músculo", "TM")]
for medium, name, code in media:
    case = "antena_" + medium + "_5px"
    meta, fit, material = index[case], analysis[case], materials[medium]
    profile = np.genfromtxt((a.campana / meta["registro"]).parent / "perfil.csv",
                            delimiter=",", names=True)
    r = profile["r_mm"]
    sr = profile["Sr_r2"]
    use = profile["usado_ajuste"].astype(bool)
    assert use.sum() == int(fit["n"])
    x, power = r[use], sr[use]
    assert np.all(power > 0)
    y = 10 * np.log10(power / power[0])
    slope = -float(fit["alpha_dB_mm"])
    intercept = np.mean(y - slope * x)
    fitted = intercept + slope * x
    residual = y - fitted
    assert abs(np.sqrt(np.mean(residual**2)) - float(fit["RMSE_dB"])) < 1e-9
    positive = sr > 0
    full_y = 10 * np.log10(np.maximum(sr[positive], np.finfo(float).tiny) / power[0])

    fig, (top, bottom) = plt.subplots(2, 1, figsize=(8.1, 6.3), sharex=True,
                                      gridspec_kw={"height_ratios": [2.5, 1]},
                                      constrained_layout=True)
    top.plot(r[positive], full_y, color="#aeb5ba", lw=1, label="Perfil radial")
    top.plot(x, y, color="#14626a", lw=1.8, label="Datos del ajuste")
    top.plot(x, fitted, color="#a34422", lw=1.6, ls="--", label="Ajuste lineal")
    top.axvspan(x.min(), x.max(), color="#14626a", alpha=.06)
    top.set(ylabel=r"$10\log_{10}(r^2\langle S_r\rangle/P_0)$ (dB)")
    top.set_title(f"{name}, 3 GHz, 5 px/mm · M-{code}5")
    top.legend(loc="best", fontsize=8)
    bottom.axhline(0, color="#4c5357", lw=.9)
    bottom.plot(x, residual, color="#674486", lw=1, marker=".", ms=2)
    bottom.set(xlabel="Distancia radial (mm)", ylabel="Residuo (dB)")
    for ax in (top, bottom): ax.grid(True, alpha=.18)
    theory = float(fit["teoria_dB_mm"])
    error = (f"{float(fit['error_abs_pct']):.3f} %" if fit["error_abs_pct"] else "no definido")
    note = (f"$\\varepsilon_r$={float(material['eps_referencia']):.3f}; "
            f"$\\sigma$={float(material['sigma_equivalente_referencia_S_m']):.3f} S/m; "
            f"$\\alpha_{{app}}$={-slope:.5f} dB/mm\n"
            f"IC 95 %: [{float(fit['IC95_inf']):.5f}, {float(fit['IC95_sup']):.5f}] dB/mm; "
            f"teoría={theory:.5f} dB/mm; error={error}\n"
            f"$R^2$={float(fit['R2']):.5f}; RMSE={float(fit['RMSE_dB']):.4f} dB; "
            f"DW={float(fit['DW']):.4f}; $n$={fit['n']}")
    fig.text(.01, -.025, note, ha="left", va="top", fontsize=8)
    dest = a.salida / f"campana61_monopolo_{code.lower()}5.png"
    fig.savefig(dest, dpi=240, bbox_inches="tight", pad_inches=.18)
    plt.close(fig)
    print(dest, meta["registro"])
