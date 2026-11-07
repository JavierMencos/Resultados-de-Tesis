from pathlib import Path
import json,csv,hashlib,shutil,re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root=Path('outputs/tesis_cierre'); base=root/'verificacion_onda_plana'
if '\\label{sec:resultados-planar}' in (root/'resultados.tex').read_text():
    raise SystemExit('La integración ya existe: no se duplicaron secciones. Usar la copia previa del documento para reproducir la integración editorial.')
shutil.copy2('outputs/tesis_fdtd/verificar_onda_plana.py',base/'verificar_onda_plana.py')
names={'vacio':'Vacío','concreto':'Concreto','agua_salada':'Agua salada','tejido_muscular':'Tejido muscular'}
codes={'vacio':'VA','concreto':'CO','agua_salada':'AS','tejido_muscular':'TM'}
data={}
for f in (base/'suave').glob('*.json'):
    d=json.loads(f.read_text()); data[d['medio'],d['px_mm']]=(d,f)
rows=[]; tex=[]
fig,axs=plt.subplots(2,2,figsize=(9,6),constrained_layout=True)
for ax,(med,name) in zip(axs.flat,names.items()):
    for res in (5,10):
        d,f=data[med,res]; m=d['muestras'][-1]; lo,hi=m['IC95_bloques']; a=m['alpha_dB_mm']
        rows.append(dict(ID=f'VP-{codes[med]}{res:02}',medio=med,px_mm=res,alpha_dB_mm=a,IC95_inf=lo,IC95_sup=hi,
          alpha_teoria_dB_mm=d['alpha_teoria_dB_mm'],error_pct=d['error_relativo_porcentaje'],
          error_abs_dB_mm=d['error_absoluto_dB_mm'],RMSE_dB=m['RMSE_dB'],cambio_temporal_flujo=d['cambio_temporal_flujo_max_rel'],
          segundos=d['segundos'],rss_max_proceso_MiB=d['rss_max_proceso_KiB']/1024,registro=f.name))
        def fmt(v):
            if med!='vacio': return f'{v:.9f}'
            mant,expo=f'{v:.2e}'.split('e')
            return rf'{mant}\times10^{{{int(expo)}}}'
        err='---' if med=='vacio' else f"{d['error_relativo_porcentaje']:.4f}"
        tex.append(rf"VP-{codes[med]}{res:02} & ${fmt(a)}$ & $[{fmt(lo)},\,{fmt(hi)}]$ & {err} \\")
        arr=np.genfromtxt(f.parent/d['perfil'],delimiter=',',names=True)
        z=arr['z_mm']; y=arr['y_dB']; pred=-d['alpha_teoria_dB_mm']*(z-z[0])
        ax.plot((z-z[0])/d['lambda_mm'],y-pred,label=f'{res} px/mm',lw=1)
    ax.set_title(name); ax.set_xlabel(r'Distancia desde el inicio / $\lambda$'); ax.set_ylabel('Perfil − teoría (dB)');ax.grid(alpha=.25);ax.legend()
fig.savefig(root/'figuras/verificacion_onda_plana.png',dpi=190);plt.close(fig)
with (base/'resumen.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)

def add(name,text):
    p=root/name;p.write_text(p.read_text(encoding='utf-8')+'\n'+text,encoding='utf-8')
add('capitulos.tex',r'''
\section{Verificación independiente mediante onda plana}\label{sec:metodo-planar}
Se añadió una prueba unidimensional de propagación uniforme a 3 GHz con los mismos valores de $\varepsilon_r$, $\sigma$ y conversión a conductividad de Meep. Se simularon los cuatro medios a 5 y 10 px/mm. Se emplearon campos complejos $E_x$ y $H_y$, un dominio de longitud $12\lambda$, capas PML de $2\lambda$ y una fuente en $z=-3\lambda$. Se extrajeron 201 puntos entre $-\lambda$ y $\lambda$, sin conductor ni interfaces materiales.

Se suavizó el encendido de la fuente continua con \texttt{width}$=2T$ y \texttt{slowness}$=6$, donde $T$ fue el período en unidades de Meep. Después de $20T+24\lambda\sqrt{\varepsilon_r}$ unidades de tiempo se tomaron dos muestras separadas por un período. Se sincronizó $H$ antes de calcular $S_z=\Re(E_xH_y^*)/2$. La variación temporal se expresó como $\max_z|S_{z,2}-S_{z,1}|/\max_z|S_{z,2}|$. Ese diagnóstico comparó únicamente los dos instantes disponibles.

Se ajustó una recta a $10\log_{10}[S_z(z)/S_z(-\lambda)]$, sin compensación geométrica ni restricción de signo sobre la pendiente. Se estimaron IC condicionales del 95\,\% con 500 réplicas de bloques de seis residuos y semilla cero. Se comparó la pendiente con $20\alpha/\ln 10$, expresada en dB/mm. La diferencia frente a la teoría y la variación entre mallas se conservaron separadas del IC. Los resultados se identificaron con el prefijo VP y las abreviaturas de medio ya definidas; 05 y 10 indicaron px/mm.
''')
add('resultados.tex',r'''
\section{Verificación de propagación uniforme}\label{sec:resultados-planar}
La campaña VP comprendió ocho corridas independientes de la antena. En los medios disipativos, los errores de atenuación respecto de la solución analítica fueron inferiores a 0.16\,\% a 5 px/mm y a 0.041\,\% a 10 px/mm (Cuadro~\ref{tab:planar}). En vacío se obtuvieron pendientes de $-2.80\times10^{-11}$ y $2.01\times10^{-10}$ dB/mm, compatibles con cero dentro de sus IC. Al ser nula la referencia, se informó la diferencia absoluta y se omitió el error relativo.

\begin{table}[htbp]\centering\footnotesize
\caption{Verificación planar: atenuación e IC condicional del 95\,\% en dB/mm. El error relativo se calculó respecto de la solución analítica. Las cifras adicionales permitieron distinguir el IC del error sistemático.}\label{tab:planar}
\begin{tabular}{lrrr}\hline
ID & $\alpha_{\rm VP}$ & IC del ajuste & Error (\%) \\ \hline
'''+ '\n'.join(tex)+r'''
\hline\end{tabular}\end{table}

La variación temporal máxima del flujo fue inferior a $7.87\times10^{-6}$ en vacío y a $2.95\times10^{-10}$ en los medios disipativos. Los RMSE fueron menores que $1.4\times10^{-5}$ dB en vacío. La Figura~\ref{fig:planar} mostró las diferencias espaciales respecto del perfil analítico, normalizado en el primer punto; las oscilaciones y la deriva restante disminuyeron al refinar la malla en los medios con pérdidas.

\begin{figure}[htbp]\centering
\includegraphics[width=\textwidth]{figuras/verificacion_onda_plana.png}
\caption{Diferencia entre el perfil planar normalizado y la predicción analítica. Cada panel utilizó su propia escala vertical. Se compararon las dos mallas sobre la misma ventana física de cada medio.}\label{fig:planar}
\end{figure}

Una ejecución inicial con encendido abrupto produjo, en vacío a 5 px/mm, un RMSE de 1.13 dB y un cambio temporal del flujo de 0.679. Se descartó como comprobación estacionaria y se conservó como diagnóstico. El cambio de activación redujo ambas discrepancias en esta prueba; los registros originales de la antena permanecieron separados. Se archivaron las dieciséis ejecuciones, sus perfiles y las dos versiones del verificador.
''')
total=sum(r['segundos'] for r in rows);rss=max(r['rss_max_proceso_MiB'] for r in rows)
add('resultados.tex',rf'Las ocho corridas con activación suave acumularon {total:.1f} s de tiempo medido y una RSS máxima del proceso de {rss:.1f} MiB. Se ejecutaron secuencialmente desde VS Code en Ubuntu con un solo hilo. La RSS fue acumulativa dentro del proceso; no se interpretó como el consumo independiente de cada caso.'+'\n')
add('discusion.tex',r'''
\section{Aporte y límites de la prueba planar}
La prueba VP reprodujo la atenuación analítica con errores mucho menores que los obtenidos para el monopolo. En agua salada, por ejemplo, el error a 5 px/mm fue de 0.1575\,\%, frente al 4.29\,\% del ajuste radial de la antena. Esta diferencia respaldó la conversión de conductividad y la propagación homogénea implementadas. A la vez, indicó que el desacuerdo del monopolo no pudo atribuirse exclusivamente a la resolución de una onda plana en ese material.

La geometría del conductor, la excitación, el campo próximo, las fronteras y la extracción radial siguieron siendo contribuciones posibles. La prueba aislada no permitió repartir cuantitativamente sus efectos. Tampoco sustituyó un refinamiento del balance cilíndrico ni resolvió la dependencia de sus potencias absolutas. El control planar en vacío sí recuperó una pendiente compatible con cero, mientras que la extracción radial histórica mantuvo su limitación.

Los IC de la prueba planar fueron estrechos y, en los medios disipativos, no incluyeron la referencia analítica. Se observó así un ejemplo directo de la diferencia entre precisión condicional del ajuste y error numérico: un perfil casi lineal produjo poca dispersión al remuestrear sus residuos, aunque conservó una pendiente ligeramente sesgada. Dos mallas permitieron evaluar sensibilidad, sin determinar por sí solas un orden asintótico. El diagnóstico inicial también mostró que una pendiente próxima a cero resultó insuficiente si el perfil mantuvo variaciones temporales importantes.
''')
add('conclusiones.tex',r'''
La verificación independiente de onda plana recuperó la atenuación teórica con errores menores que 0.16\,\% a 5 px/mm en los medios disipativos y una pendiente compatible con cero en vacío. Este control respaldó la implementación del medio homogéneo. Su alcance se distinguió de la validación del monopolo, cuyo refinamiento geométrico y convergencia de potencias absolutas permanecieron limitados.
''')
add('anexos_A.tex',r'''
\section{Archivos de la verificación planar}
Se conservaron el código \texttt{verificar\_onda\_plana.py}, los CSV de campos complejos y flujo, los JSON de parámetros y ajuste, el cuadro resumen y los hashes en \href{https://github.com/JavierMencos/Resultados-de-Tesis/tree/main/Tesis_Resultados/Verificacion_1D}{Tesis\_Resultados/Verificacion\_1D}. La carpeta \texttt{diagnostico\_inicial} contuvo los ocho casos de encendido abrupto y su código; \texttt{suave} contuvo los ocho casos utilizados en el Cuadro~\ref{tab:planar}. El índice relacionó cada VP con su nombre fechado. Se documentó el cambio de activación sin sobrescribir los resultados previos.

\section{Trazabilidad de los objetivos y del alcance}
El objetivo general y el primer objetivo específico quedaron respaldados para la atenuación dentro de medios homogéneos por los perfiles radiales, la comparación analítica, el refinamiento y la prueba planar. La penetración a través de interfaces no se simuló y quedó fuera de la evidencia obtenida. Para el segundo objetivo se definieron ventanas, unidades, normalización, diagnósticos y un procedimiento reproducible, cuyo alcance fue interno a la campaña. Para el tercero se obtuvo una representación radial relativa, sin validación predictiva frente a datos independientes. Esta delimitación se conservó al evaluar el cumplimiento de los objetivos originales.
''')
p=root/'teoria.tex';s=p.read_text();start=s.index('y, para dos contornos,');end=s.index('Otro componente del aporte',start)
s=s[:start]+r'''Para el anillo sin fuentes se evaluó $P_{\rm ent}-P_{\rm sal}-P_{\rm J}$. Su residuo, normalizado por la entrada, cuantificó el cierre entre las cuatro caras y el volumen. Se distinguió de una eficiencia global de la antena y de una estimación del error al continuo.

'''+s[end:];s=s.replace('qué fracción de la energía suministrada se disipa antes de alcanzar un contorno determinado','qué fracción de la energía que entró en el volumen de control se disipó en él');p.write_text(s,encoding='utf-8')
(base/'README.md').write_text(f'''# Verificación de propagación homogénea 1D

VP = verificación planar; VA vacío, CO concreto, AS agua salada, TM tejido muscular. 05/10 = px/mm.
No es una corrida de antena ni un balance cilíndrico. Fuente no calibrada en SI.

`diagnostico_inicial`: ocho corridas con fuente abrupta; el vacío no cumplió estabilidad temporal. Se conservan por trazabilidad.
`suave`: ocho corridas con encendido width=2T, slowness=6. Sus campos, ajustes, IC y metadatos se resumieron en `resumen.csv`.
Ambas versiones se ejecutaron en VS Code/Ubuntu, secuencialmente y con un hilo. Código y resultados no se mezclan.

Reproducción: ejecutar `verificar_onda_plana.py` en el entorno Meep de la tesis mediante la tarea de VS Code incluida. Cada ejecución genera nombres UTC nuevos. `integrar_verificacion.py` conserva el procedimiento de análisis y generación de la figura; requiere adaptar la raíz del documento al lugar de descarga.
Los IC son condicionales al perfil determinista. No incluyen incertidumbre de parámetros materiales, frontera, tiempo ni discretización.
El control temporal usa dos instantes separados por T, y no garantiza ausencia de oscilaciones más lentas.
Con activación suave: suma de tiempos {total:.3f} s; máximo RSS acumulativo {rss:.3f} MiB.
La reducción de error frente a la teoría respalda esta configuración planar; no certifica convergencia de amplitudes del monopolo.
''',encoding='utf-8')
shutil.copy2(__file__,base/'integrar_verificacion.py')
(base/'SHA256SUMS').write_text('\n'.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(base).as_posix()}' for p in sorted(base.rglob('*')) if p.is_file() and p.name!='SHA256SUMS')+'\n')
print('Simulaciones',len(rows),'segundos',total,'RSS',rss)
