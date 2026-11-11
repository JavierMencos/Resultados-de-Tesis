"""Genera la figura de control después de ejecutar verificar.py."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parent
plt.rcParams.update({"svg.hashsalt": "tesis-3GHz", "font.size": 10})
with (root/"atenuacion.csv").open(encoding="utf-8") as f:
    water = [r for r in csv.DictReader(f) if r["id"].startswith("antena_agua_salada_") and "pml" not in r["id"]]
water.sort(key=lambda r: int(r["id"].split("_")[-1][:-2]))
with (root/"balance_anular.csv").open(encoding="utf-8") as f:
    balances = {r["id"]: r for r in csv.DictReader(f)}
fig, (ax, bx) = plt.subplots(1, 2, figsize=(9.4, 4.1), constrained_layout=True)
res = [int(r["id"].split("_")[-1][:-2]) for r in water]
slopes = [float(r["alpha_dB_mm"]) for r in water]
errors = [[abs(y-float(r[k])) for y,r in zip(slopes,water)] for k in ("IC95_inf","IC95_sup")]
ax.errorbar(res, slopes, yerr=errors, fmt="o-", capsize=4, label="Antena e IC del ajuste")
ax.axhline(float(water[0]["teoria_dB_mm"]), ls="--", color="#a04628", label="Teoría de onda plana")
ax.set(xlabel="Resolución (px/mm)", ylabel="Atenuación (dB/mm)", title="Agua marina a 3 GHz", xticks=res)
ax.legend(fontsize=8)
media = ["vacio","concreto","tejido_muscular","agua_salada"]
values = [100*float(balances[f"antena_{m}_5px"]["fraccion_disipada"]) for m in media]
bars = bx.barh(["Vacío","Concreto","Músculo","Agua marina"], values, color="#337678")
bx.bar_label(bars, fmt="%.2f", padding=3)
bx.set(xlabel="Potencia disipada / entrante (%)", title="Balance local a 5 px/mm", xlim=(0,106))
fig.savefig(root/"verificacion.svg", metadata={"Date":None})
plt.close(fig)
