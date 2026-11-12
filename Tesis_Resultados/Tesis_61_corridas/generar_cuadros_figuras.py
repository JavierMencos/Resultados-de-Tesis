"""Cuadros y figuras de tesis a partir del archivo público de 61 corridas."""
import csv
import argparse
import json
import math
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--campana",type=Path,default=HERE/"cierre_campana_git/Tesis_Resultados/Campana_Referencias_20261107")
parser.add_argument("--salida",type=Path,default=HERE/"tesis_61")
opts=parser.parse_args()
C=opts.campana.resolve()
D=opts.salida.resolve()
(D/"figuras").mkdir(parents=True,exist_ok=True)
def read(name):
    with (C/name).open(encoding="utf8",newline="") as f:
        return list(csv.DictReader(f))
def write(name,content):
    (D/name).write_text(content.strip()+"\n",encoding="utf8")
def num(v):
    if v=="" or v is None: return "---"
    n=float(v)
    if n==0: return "$0$"
    if abs(n)<.001 or abs(n)>=10000:
        a,b=f"{n:.3e}".split("e")
        return "$"+a+r"\times 10^{"+str(int(b))+"}$"
    return "$"+format(n,".5g")+"$"
def table(title,label,head,rows):
    h=" & ".join(head)+r" \\ \hline"
    return "\n".join([r"\begingroup\small\setlength{\tabcolsep}{4pt}",r"\begin{longtable}{l"+"r"*(len(head)-1)+"}",r"\caption{"+title+r"}\label{"+label+r"}\\",r"\hline "+h+r"\endfirsthead",r"\hline "+h+r"\endhead",*[" & ".join(row)+r" \\" for row in rows],r"\hline\end{longtable}\endgroup",""])
idx=read("indice_corridas.csv")
ix={r["id"]:r for r in idx}
media={"vacio":"Vacío","concreto":"Concreto","agua_salada":"Agua marina","tejido_muscular":"Músculo"}
codes={"vacio":"VA","concreto":"CO","agua_salada":"AS","tejido_muscular":"TM"}
def code(i):
    r=ix[i]
    k={"antena":"M","lamina":"L","plana":"P"}[r["tipo"]]+"-"+codes[r["medio"]]+r["px_mm"]
    if r["tipo"]=="lamina": k+="-"+i.split("px_")[1].split("mm")[0]
    return k+("*" if "_pml3" in i else "")
att=read("analisis/atenuacion.csv");bal=read("analisis/balance_anular.csv");sl=read("analisis/laminas.csv")
sens=read("analisis/sensibilidad.csv");ordr=read("analisis/refinamiento_agua.csv")
for row in sl:
    row["A_integral"]=row["A"]
keys={"alpha_dB_mm":r"$\alpha_{\rm app}$","entrada_M":r"$P_e$","salida_M":r"$P_s$","joule_M":r"$P_J$","fraccion_disipada":r"$f_J$","residuo_pct":r"$b$"}
def vals(r,ks):return [num(r[k]) for k in ks.split()]
def by(r): return r["id"].startswith("antena_") and r["id"].endswith("_5px")
tab=table(r"Atenuación aparente del monopolo a 5 px/mm. Pendientes e intervalos del 95\,\% en dB/mm. El error relativo se calculó respecto de la onda plana.","t:principal",["Medio",r"$\alpha_{\rm app}$","IC inferior","IC superior",r"$\alpha_{\rm teo}$",r"Error (\%)"],[[media[ix[r["id"]]["medio"]]]+vals(r,"alpha_dB_mm IC95_inf IC95_sup teoria_dB_mm error_abs_pct") for r in att if by(r)])
write("cuadro_principal.tex",tab)
tab=table(r"Balance del anillo a 5 px/mm. Las potencias se expresaron en unidades de Meep. Las dos últimas columnas se normalizaron por la entrada.","t:balance",["Medio",r"$P_e$",r"$P_s$",r"$P_J$",r"$f_J$ (\%)",r"$b$ (\%)"],[[media[ix[r["id"]]["medio"]]]+vals(r,"entrada_M salida_M joule_M")+[num(100*float(r["fraccion_disipada"])),num(r["residuo_pct"])] for r in bal if by(r)])
write("cuadro_balance.tex",tab)
a=r"""\chapter{Registros numéricos de la campaña}\label{an:fdtd-fuentes}
Los códigos de este anexo identifican el ensayo, el medio y la resolución. P designa onda plana, L lámina y M monopolo. VA indica vacío, CO concreto, AS agua marina y TM tejido muscular. Así, M-AS5 corresponde al monopolo en agua marina a 5 px/mm. En las láminas, el número posterior al segundo guion es el espesor en mm. El asterisco identifica la capa absorbente de tres longitudes de onda. Para las láminas se utilizó la longitud de onda del vacío y para el monopolo la del medio.
\section{Índice de corridas y recursos}
Los tiempos correspondieron a cada simulación completa y la memoria al máximo residente del proceso. Los tres intentos interrumpidos de vacío se conservaron como registros de ejecución. El índice identifica únicamente los 61 resultados aceptados.
"""
a+=table("Inventario de corridas con ubicación definida por el código, tiempo y memoria.","t:inv",["Caso",r"$\lambda_m$ (mm)",r"Celdas/$\lambda_m$","Tiempo (min)","Memoria (MiB)"],[[code(r["id"])]+vals(r,"lambda_mm celdas_por_lambda")+[num(float(r["segundos"])/60),num(float(r["rss_max_KiB"])/1024)] for r in idx])
a+=r"""\section{Pendientes, intervalos y diagnóstico del ajuste}
Las pendientes, sus diferencias y los límites de los intervalos se presentan en dB/mm. En vacío la referencia fue cero y el error porcentual quedó indefinido. El guion representa un valor que no corresponde a ese caso.
"""
a+=table("Atenuación en ondas planas y monopolos. Diferencia firmada respecto de la teoría.","t:atte",["Caso","Ajuste","Teoría","Diferencia","Error (\\%)","IC inf.","IC sup."],[[code(r["id"])]+vals(r,"alpha_dB_mm teoria_dB_mm diferencia_dB_mm error_abs_pct IC95_inf IC95_sup") for r in att])
a+=table("Diagnóstico por perfil. DW es el estadístico de Durbin--Watson. Los extremos corresponden a las pendientes obtenidas al variar el inicio de la ventana.","t:diag",["Caso","Puntos",r"$L$",r"$R^2$","RMSE (dB)","DW","Mín.","Máx."],[[code(r["id"])]+vals(r,"n bloque R2 RMSE_dB DW ventana_min_dB_mm ventana_max_dB_mm") for r in att])
a+=table("Sensibilidad del intervalo del 95\\,\\% al duplicar y cuadruplicar la longitud de bloque, en dB/mm.","t:ic",["Caso",r"Inf. $2L$",r"Sup. $2L$",r"Inf. $4L$",r"Sup. $4L$"],[[code(r["id"])]+vals(r,"IC95_inf_Lx2 IC95_sup_Lx2 IC95_inf_Lx4 IC95_sup_Lx4") for r in att])
a+=r"\section{Energía y estacionariedad}"+"\n"
a+=table("Potencias del anillo en unidades de Meep, fracción disipada y residuo porcentual.","t:ban",["Caso",r"$P_e$",r"$P_s$",r"$P_J$",r"$f_J$",r"$b$ (\%)"],[[code(r["id"])]+vals(r,"entrada_M salida_M joule_M fraccion_disipada residuo_pct") for r in bal])
a+=table("Cambio relativo del perfil radial en la última comparación y máximo de los dos últimos cambios del diagnóstico energético.","t:temp",["Caso","Perfil","Diagnóstico"],[[code(r["id"])]+vals(r,"var_temporal_perfil var_temporal_diagnostico") for r in bal])
a+=r"""\section{Sensibilidad de malla y frontera}
Cada par compara el primer caso con el segundo. Se muestran las diferencias firmadas y los porcentajes relativos al valor absoluto de la referencia. Para el residuo $b$, la diferencia se expresa en puntos porcentuales. Los valores individuales se encuentran en los cuadros precedentes.
"""
for j,kk in enumerate((list(keys)[:3],list(keys)[3:])):
    pairs={}
    for r in sens:pairs.setdefault((r["caso"],r["referencia"]),{})[r["magnitud"]]=r
    title=("Efecto de la malla y la frontera sobre la pendiente y las potencias entrante y saliente." if j==0 else "Efecto de la malla y la frontera sobre la disipación, su fracción y el residuo del balance.")
    a+=table(title,"t:sens"+str(j),["Par"]+sum(([keys[k],r"\%"] for k in kk),[]),[[code(p)+"/"+code(q)]+sum((vals(rows[k],"diferencia diferencia_rel_pct") for k in kk),[]) for (p,q),rows in pairs.items()]).replace(r"\small\setlength{\tabcolsep}{4pt}",r"\footnotesize\setlength{\tabcolsep}{1.5pt}")
a+=table("Refinamiento en agua marina. Valores por resolución y orden aparente de la terna 5/10/20.","t:orden",["Magnitud","5","10","15","20","Monótona",r"$p$"],[[keys[r["magnitud"]]]+vals(r,"q5 q10 q15 q20")+["Sí" if r["monotona_4"]=="True" else "No",num(r["orden_aparente_5_10_20"])] for r in ordr])
a+=table("Extrapolación condicional en agua. Las diferencias conservan las unidades de la magnitud. Estos valores diagnostican la estabilidad de la extrapolación.","t:extrap",["Magnitud","Límite formal",r"Límite menos $q_{20}$",r"Predicción menos $q_{15}$"],[[keys[r["magnitud"]]]+vals(r,"limite_condicional estimacion_menos_q20 prediccion_menos_q15") for r in ordr])
write("anexos_A.tex",a)
b=r"""\chapter{Transmisión por láminas y archivos reproducibles}
\section{Reflexión, transmisión y absorción}
Los coeficientes $R$, $T$ y $A$ son fracciones de la potencia incidente. Las diferencias entre cálculo numérico y teoría, así como el residuo $100(1-R-T-A)$, se expresan en puntos porcentuales. Los casos de 30 mm de concreto y 7 mm de agua y músculo se reservaron para contrastar la predicción con la solución de lámina a espesores distintos de los restantes.
"""
b+=table("Resultados de las 41 configuraciones de lámina. La pérdida de inserción se expresó en dB.","t:lam",["Caso",r"$R$",r"$T$",r"$A$",r"$L_i$ (dB)","Residuo (pp)"],[[code(r["id"])]+vals(r,"R T A_integral perdida_insercion_dB residuo_pp") for r in sl])
b+=table("Coeficientes teóricos y diferencias numéricas firmadas en puntos porcentuales.","t:lamt",["Caso",r"$R_t$",r"$T_t$",r"$A_t$",r"$\Delta R$",r"$\Delta T$",r"$\Delta A$"],[[code(r["id"])]+vals(r,"R_teoria T_teoria A_teoria R_error_pp T_error_pp A_error_pp") for r in sl])
url="https://github.com/JavierMencos/Resultados-de-Tesis/tree/dcbbe9551d1a23f3a738add5e25c5f818cc6d5c8/Tesis_Resultados/Campana_Referencias_20261107"
b+=r"""\section{Acceso a los datos}
La \href{URL}{versión archivada de la campaña de 3 GHz} reúne el simulador, los parámetros materiales y el índice de las 61 corridas. Cada fila del índice enlaza la configuración con el directorio de sus campos y resultados. En \href{URL/analisis}{el directorio de análisis} se incluyen el código de verificación, las tablas a precisión completa y la figura de refinamiento y balance. El archivo \texttt{SHA256SUMS} permite comprobar la integridad de la descarga.
""".replace("URL",url)
write("anexos_B.tex",b)
# Misma figura y datos del repositorio, en formato que admite pdfLaTeX.
import runpy, tempfile, shutil
with tempfile.TemporaryDirectory() as tmp:
    for name in ["figura.py","atenuacion.csv","balance_anular.csv"]:
        shutil.copy2(C/"analisis"/name,Path(tmp)/name)
    figdata=runpy.run_path(str(Path(tmp)/"figura.py"))
figdata["fig"].savefig(D/"figuras/campana61_verificacion.png",dpi=220,bbox_inches="tight")
fig,axes=plt.subplots(2,2,figsize=(8,5.8),constrained_layout=True)
for r,ax in zip([r for r in idx if by(r)],axes.flat):
    folder=(C/r["registro"]).parent
    d=np.genfromtxt(folder/"perfil.csv",names=True,delimiter=",")
    mask=d["usado_ajuste"].astype(bool); x=d["r_mm"][mask]; y=10*np.log10(d["Sr_r2"][mask]/d["Sr_r2"][mask][0])
    ax.plot(x,y,label="FDTD",color="#126368");ax.plot(x,np.polyval(np.polyfit(x,y,1),x),"--",label="Ajuste",color="#a74618")
    ax.set(title=media[r["medio"]],xlabel="Distancia radial (mm)",ylabel="Flujo compensado (dB)");ax.legend(fontsize=8)
fig.savefig(D/"figuras/campana61_perfiles.png",dpi=220)
plt.close(fig)
fig,axes=plt.subplots(1,3,figsize=(9,3.2),constrained_layout=True,sharey=True)
for ax,m in zip(axes,["concreto","agua_salada","tejido_muscular"]):
    rows=sorted((r for r in sl if ix[r["id"]]["medio"]==m and ix[r["id"]]["px_mm"]=="5" and "*" not in code(r["id"])),key=lambda r:float(r["espesor_mm"]))
    x=[float(r["espesor_mm"]) for r in rows]
    for key,mark in zip(("R","T","A_integral"),("o","s","^")):
        ax.plot(x,[float(r[key]) for r in rows],marker=mark,label=key[0])
    ax.set(title=media[m],xlabel="Espesor (mm)",ylim=(0,1));ax.legend(fontsize=8)
axes[0].set_ylabel("Fracción de potencia incidente");fig.savefig(D/"figuras/campana61_laminas.png",dpi=220)
plt.close(fig)
