"""Verificación FDTD 1D independiente de la geometría de la antena.

Ejecutar con un hilo desde la tarea de VS Code. No calibra la fuente en SI.
Se guardan todas las muestras, residuos, parámetros y metadatos por malla.
Los IC por bloques son condicionales al ajuste de un perfil determinista;
no representan incertidumbre material ni error de discretización.
"""
import os
os.environ['OMP_NUM_THREADS']='1'
os.environ['OPENBLAS_NUM_THREADS']='1'
import csv,json,time,resource,platform,hashlib
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import meep as mp

F=3e9; C=299792458.; EPS0=8.854e-12; MU0=4*np.pi*1e-7
T=C/F*1e3
MATERIALES={'vacio':(1.,0.),'concreto':(4.5,.05),'agua_salada':(78.,4.),'tejido_muscular':(52.7,2.2)}
DESTINO=Path(__file__).resolve().parent/'corridas'/'verificacion_onda_plana_suave'
DESTINO.mkdir(parents=True,exist_ok=True)
SCRIPT_SHA=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

def parametros(epsr,sigma):
    td=sigma/(2*np.pi*F*EPS0*epsr)
    s=np.sqrt(1+td*td); pref=2*np.pi*F*np.sqrt(MU0*EPS0*epsr/2)
    alpha=pref*np.sqrt(td*td/(s+1)); beta=pref*np.sqrt(s+1)
    return alpha*20/np.log(10)/1000,2*np.pi/beta*1000,sigma*.001/(EPS0*C*epsr)

def ajustar(z,flujo):
    if not np.all(np.isfinite(flujo)) or np.any(flujo<=0):
        raise ValueError('El flujo de la ventana no fue estrictamente positivo')
    x=z-z.mean(); y=10*np.log10(flujo/flujo[0])
    A=np.column_stack((np.ones(len(x)),x)); coef=np.linalg.lstsq(A,y,rcond=None)[0]
    yp=A@coef; resid=y-yp; n=len(x); L=max(5,round(n**(1/3)))
    rng=np.random.default_rng(0); replicas=[]
    for _ in range(500):
        inicio=rng.integers(0,n-L+1,size=int(np.ceil(n/L)))
        e=np.concatenate([resid[j:j+L] for j in inicio])[:n]
        replicas.append(float(-np.linalg.lstsq(A,yp+e,rcond=None)[0][1]))
    return dict(alpha_dB_mm=float(-coef[1]),IC95_bloques=np.quantile(replicas,[.025,.975]).tolist(),
                RMSE_dB=float(np.sqrt(np.mean(resid**2))),bloque=L,replicas=500,
                semilla=0,condicion='IC condicional al ajuste; no incertidumbre total'),y,yp,resid

def corrida(medio,resolucion):
    inicio=time.monotonic(); epsr,sigma=MATERIALES[medio]; ateo,lam,sigD=parametros(epsr,sigma)
    material=mp.Medium(epsilon=epsr,D_conductivity=sigD)
    sim=mp.Simulation(cell_size=mp.Vector3(0,0,12*lam),dimensions=1,
        boundary_layers=[mp.PML(2*lam)],default_material=material,resolution=resolucion,
        sources=[mp.Source(mp.ContinuousSource(frequency=1/T,width=2*T,slowness=6,is_integrated=True),component=mp.Ex,
                           center=mp.Vector3(0,0,-3*lam))],force_complex_fields=True,Courant=.5)
    z=np.linspace(-lam,lam,201); muestras=[]; perfiles=[]
    def medir(s):
        ex=np.array([s.get_field_point(mp.Ex,mp.Vector3(0,0,p)) for p in z])
        hy=np.array([s.get_field_point(mp.Hy,mp.Vector3(0,0,p)) for p in z])
        flujo=.5*np.real(ex*np.conj(hy)); fit,y,yp,r=ajustar(z,flujo)
        muestras.append(dict(t_M=float(s.meep_time()),**fit)); perfiles.append((ex,hy,flujo,y,yp,r))
    duracion=20*T+2*(12*lam*np.sqrt(epsr))
    for dur in (duracion,T): sim.run(mp.at_end(mp.synchronized_magnetic(medir)),until=dur)
    ex,hy,p,y,yp,r=perfiles[-1]
    marca=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    base=f'VP_{medio}_{resolucion}px_{marca}'
    with (DESTINO/(base+'.csv')).open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['z_mm','Ex_real_M','Ex_imag_M','Hy_real_M','Hy_imag_M','Sz_M','Sz_M_muestra1','y_dB','ajuste_dB','residuo_dB'])
        w.writerows(zip(z,ex.real,ex.imag,hy.real,hy.imag,p,perfiles[0][2],y,yp,r))
    error=abs(muestras[-1]['alpha_dB_mm']-ateo)
    registro=dict(tipo='verificacion_onda_plana_1D',medio=medio,px_mm=resolucion,epsr=epsr,sigma_S_m=sigma,
        frecuencia_Hz=F,longitud_referencia_mm=1,lambda_mm=lam,sigmaD=sigD,alpha_teoria_dB_mm=ateo,
        encendido='suave',width_tM=2*T,slowness=6,
        error_absoluto_dB_mm=error,error_relativo_porcentaje=100*error/ateo if ateo else None,
        dominio_z_mm=[-6*lam,6*lam],pml_espesor_mm=2*lam,fuente_z_mm=-3*lam,ventana_z_mm=[-lam,lam],
        muestras=muestras,cambio_temporal_alpha_dB_mm=abs(muestras[1]['alpha_dB_mm']-muestras[0]['alpha_dB_mm']),
        cambio_temporal_flujo_max_rel=float(np.max(np.abs(p-perfiles[0][2]))/np.max(np.abs(p))),
        segundos=time.monotonic()-inicio,rss_max_proceso_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        meep=mp.__version__,python=platform.python_version(),sistema=platform.platform(),hilos=1,
        script_sha256=SCRIPT_SHA,perfil=base+'.csv',fuente_calibrada=False)
    (DESTINO/(base+'.json')).write_text(json.dumps(registro,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    print('REGISTRO',base,'alpha',muestras[-1]['alpha_dB_mm'],'error_pct',registro['error_relativo_porcentaje'],flush=True)
    sim.reset_meep()

if __name__=='__main__':
    for material in MATERIALES:
        for res in (5,10): corrida(material,res)
