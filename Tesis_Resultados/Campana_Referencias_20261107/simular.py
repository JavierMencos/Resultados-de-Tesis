"""Campaña FDTD a 3 GHz con materiales trazables. Un caso por proceso.

Longitudes en mm; campos y potencias normalizados de Meep. El modelo
epsilon real + conductividad equivalente representa la frecuencia central.
No se atribuye al transitorio la dispersión completa del material real.
"""
import os
os.environ['OMP_NUM_THREADS']='1'
os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse, csv, hashlib, json, platform, resource, time
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import meep as mp

ROOT=Path(__file__).resolve().parent
C=299792458.; EPS0=8.8541878128e-12; MU0=1/(EPS0*C*C)
F=3e9; T=C/F*1000
M={r['medio']:(float(r['eps_referencia']),float(r['sigma_equivalente_referencia_S_m']))
   for r in csv.DictReader((ROOT/'materiales.csv').open())}


def save_json(p,value):
    tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8');tmp.replace(p)


def theory(eps,sigma):
    n=np.sqrt(complex(eps,sigma/(2*np.pi*F*EPS0)))
    return float(2*np.pi/T*n.imag*20/np.log(10)),float(T/n.real),sigma*.001/(EPS0*C*eps)


def fit(x,p):
    y=10*np.log10(p/p[0]);xx=x-x.mean();A=np.column_stack((np.ones(len(x)),xx))
    b=np.linalg.lstsq(A,y,rcond=None)[0];pred=A@b;res=y-pred
    n=len(x);L=max(5,round(n**(1/3)));rng=np.random.default_rng(0)
    boot=[]
    for _ in range(1500):
        starts=rng.integers(0,n-L+1,size=int(np.ceil(n/L)))
        e=np.concatenate([res[k:k+L] for k in starts])[:n]
        boot.append(float(-np.linalg.lstsq(A,pred+e,rcond=None)[0][1]))
    rss=float(res@res);sst=float((y-y.mean())@(y-y.mean()))
    return dict(alpha_dB_mm=float(-b[1]),IC95_ajuste_bloques=np.quantile(boot,[.025,.975]).tolist(),
        RMSE_dB=float(np.sqrt(rss/n)),R2=1-rss/sst if sst>0 else None,
        Durbin_Watson=float(np.diff(res)@np.diff(res)/rss) if rss>0 else None,
        n=n,bloque=L,replicas=1500,semilla=0,modelo='M0 lineal sin restriccion de signo',
        advertencia='IC condicional al perfil; no incluye incertidumbre material ni discretizacion')


def fields(sim,z,components,radial=False):
    return np.array([[sim.get_field_point(c,mp.Vector3(float(v),0,0) if radial else mp.Vector3(0,0,float(v))) for v in z] for c in components])


def relative_change(a,b):
    return float(np.max(np.abs(np.asarray(a)-np.asarray(b)))/max(float(np.max(np.abs(a))),1e-100))


def run_samples(sim,measure,duration,folder):
    samples=[]
    def callback(s):
        samples.append(measure(s))
        save_json(folder/'progreso_fisico.json',dict(t_M=float(s.meep_time()),muestras=len(samples)))
    sim.run(mp.at_end(mp.synchronized_magnetic(callback)),until=duration)
    changes=[]
    for k in range(5):
        sim.run(mp.at_end(mp.synchronized_magnetic(callback)),until=(1 if k<2 else 4)*T)
        changes.append(relative_change(samples[-2]['diagnostico'],samples[-1]['diagnostico']))
        if len(changes)>=2 and max(changes[-2:])<1e-4:break
    return samples,changes


def homogeneous(args,folder,eps,sigma,alpha,lam,sd):
    sim=mp.Simulation(cell_size=mp.Vector3(0,0,12*lam),dimensions=1,resolution=args.res,
        boundary_layers=[mp.PML(args.pml*lam)],default_material=mp.Medium(epsilon=eps,D_conductivity=sd),
        sources=[mp.Source(mp.ContinuousSource(frequency=1/T,width=2*T,slowness=6,is_integrated=True),
                           component=mp.Ex,center=mp.Vector3(0,0,-3*lam))],force_complex_fields=True)
    z=np.linspace(-lam,lam,401)
    def measure(s):
        e,h=fields(s,z,(mp.Ex,mp.Hy));p=.5*np.real(e*np.conj(h))
        return dict(t_M=float(s.meep_time()),e=e,h=h,p=p,diagnostico=p)
    samples,changes=run_samples(sim,measure,20*T+24*lam*np.sqrt(eps),folder)
    last=samples[-1]
    with (folder/'perfil.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['z_mm','Ex_real','Ex_imag','Hy_real','Hy_imag','Sz','Sz_anterior'])
        w.writerows(zip(z,last['e'].real,last['e'].imag,last['h'].real,last['h'].imag,last['p'],samples[-2]['p']))
    fitted=fit(z,last['p'])
    return dict(ajuste=fitted,discrepancia_teoria_dB_mm=abs(fitted['alpha_dB_mm']-alpha),
                cambio_temporal=changes,estacionario=max(changes[-2:])<1e-4,tiempos_M=[s['t_M'] for s in samples])


def slab(args,folder,eps,sigma,alpha,lam,sd):
    d=args.d;pad=args.pml*T;length=d+4*T+2*pad
    monitors=[-d/2-T/2,d/2+T/2];z=np.linspace(-d/2,d/2,max(3,int(round(d*args.res))+1))
    results=[]
    for empty in (True,False):
        mat=mp.Medium(epsilon=eps,D_conductivity=sd)
        sim=mp.Simulation(cell_size=mp.Vector3(0,0,length),dimensions=1,resolution=args.res,
            boundary_layers=[mp.PML(pad)],force_complex_fields=True,
            geometry=[] if empty else [mp.Block(size=mp.Vector3(mp.inf,mp.inf,d),material=mat)],
            sources=[mp.Source(mp.ContinuousSource(frequency=1/T,width=2*T,slowness=6,is_integrated=True),
                               component=mp.Ex,center=mp.Vector3(0,0,-d/2-1.5*T))])
        def measure(s):
            e,h=fields(s,monitors,(mp.Ex,mp.Hy));ev=fields(s,z,(mp.Ex,))[0]
            p=.5*np.real(e*np.conj(h));loss=.5*eps*sd*np.trapezoid(abs(ev)**2,z) if not empty else 0.
            return dict(t_M=float(s.meep_time()),e=e,h=h,ev=ev,p=p,loss=float(loss),diagnostico=[*p,loss])
        samples,changes=run_samples(sim,measure,30*T+4*(d*np.sqrt(eps)+4*T),folder)
        results.append((samples[-1],changes));sim.reset_meep()
    inc,ci=results[0];obj,co=results[1]
    incident=float(inc['p'][0]);reflected=-.5*float(np.real((obj['e'][0]-inc['e'][0])*np.conj(obj['h'][0]-inc['h'][0])))
    R=reflected/incident;Tr=float(obj['p'][1]/incident);A=obj['loss']/incident
    n=np.sqrt(complex(eps,sigma/(2*np.pi*F*EPS0)));r=(1-n)/(1+n);p=np.exp(1j*2*np.pi/T*n*d)
    rr=r*(1-p*p)/(1-r*r*p*p);tt=(1-r*r)*p/(1-r*r*p*p)
    exact=[float(abs(rr)**2),float(abs(tt)**2),float(1-abs(rr)**2-abs(tt)**2)]
    with (folder/'campos_lamina.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['z_mm','Ex_real','Ex_imag','Joule_vol_M']);w.writerows(zip(z,obj['ev'].real,obj['ev'].imag,.5*eps*sd*abs(obj['ev'])**2))
    return dict(espesor_mm=d,R=R,T=Tr,A_integral=A,residuo_balance=1-R-Tr-A,
        teoria_RTA=exact,error_RTA_absoluto=[abs(v-e) for v,e in zip((R,Tr,A),exact)],
        perdida_insercion_dB=float(-10*np.log10(Tr)),perdida_absorcion_bulk_dB=alpha*d,
        incidente=incident,monitores_z_mm=monitors,calibracion=inc['p'].tolist(),
        campos_monitores_objeto=[[float(v.real),float(v.imag)] for v in [*obj['e'],*obj['h']]],
        cambio_temporal=co,cambio_temporal_referencia=ci,estacionario=max(co[-2:]+ci[-2:])<1e-4,
        validacion_independiente=args.validacion)


def antenna(args,folder,eps,sigma,alpha,lam,sd):
    rmax=5*lam;pad=args.pml*lam;zmax=.5*lam+4*lam+2*pad;gap=.4;arm=(.5*lam-gap)/2
    geometry=[mp.Block(material=mp.metal,center=mp.Vector3(rmax/2,0,-zmax/2-gap/2),size=mp.Vector3(mp.inf,0,zmax)),
              mp.Cylinder(material=mp.metal,radius=.2,height=arm,center=mp.Vector3(0,0,gap/2+arm/2))]
    sim=mp.Simulation(cell_size=mp.Vector3(rmax+pad,0,zmax),boundary_layers=[mp.PML(pad,direction=mp.R),mp.PML(pad,direction=mp.Z)],
        geometry=geometry,default_material=mp.Medium(epsilon=eps,D_conductivity=sd),resolution=args.res,
        dimensions=mp.CYLINDRICAL,m=0,eps_averaging=True,force_complex_fields=True,
        sources=[mp.Source(mp.ContinuousSource(frequency=1/T,width=2*T,slowness=6,is_integrated=True),
                           component=mp.Ez,center=mp.Vector3(),size=mp.Vector3(.4,0,gap))])
    r=np.linspace(.25*lam,5*lam,int(np.ceil(4.75*lam*args.res))+1)
    nr=int(np.ceil(lam*args.res))+1;rv=np.linspace(lam,2*lam,nr);zv=np.linspace(.25*lam,1.25*lam,nr)
    def measure(s):
        ez,hp=fields(s,r,(mp.Ez,mp.Hp),True);sr=-.5*np.real(ez*np.conj(hp))
        # Volumen sin fuentes ni metal; campos interpolados en límites físicos idénticos.
        er,ev,hv=np.empty((3,nr,nr),dtype=complex)
        for i,radio in enumerate(rv):
            for j,altura in enumerate(zv):
                point=mp.Vector3(float(radio),0,float(altura))
                er[i,j],ev[i,j],hv[i,j]=[s.get_field_point(c,point) for c in (mp.Er,mp.Ez,mp.Hp)]
        pr=-.5*np.real(ev*np.conj(hv));pz=.5*np.real(er*np.conj(hv));area=2*np.pi*rv
        faces=np.array([-area[0]*np.trapezoid(pr[0],zv),area[-1]*np.trapezoid(pr[-1],zv),
                        -np.trapezoid(area*pz[:,0],rv),np.trapezoid(area*pz[:,-1],rv)])
        loss=float(np.trapezoid(area*np.trapezoid(.5*eps*sd*(abs(er)**2+abs(ev)**2),zv,axis=1),rv))
        pin=float(-faces[faces<0].sum());pout=float(faces[faces>0].sum())
        return dict(t_M=float(s.meep_time()),ez=ez,hp=hp,sr=sr,diagnostico=[*faces,loss],
                    balance=dict(caras_salientes=faces.tolist(),entrada=pin,salida=pout,joule=loss,
                                 residuo_rel=(pin-pout-loss)/pin,fraccion_disipada=loss/pin))
    samples,changes=run_samples(sim,measure,20*T+3*rmax*np.sqrt(eps),folder)
    last=samples[-1];p=last['sr']*r*r
    lo=1.5 if args.medio in ('vacio','concreto') else 2.
    mask=(r>lo*lam)&(r<4*lam)&(p>0)&(abs(p)>np.max(abs(p))*1e-8)
    fitted=fit(r[mask],p[mask]) if mask.sum()>20 else None
    window=[]
    for low in (1.5,2,2.5,3):
        m=(r>low*lam)&(r<4*lam)&(p>0)&(abs(p)>np.max(abs(p))*1e-8)
        if m.sum()>20:window.append(dict(inferior_lambda=low,alpha_dB_mm=float(-np.polyfit(r[m],10*np.log10(p[m]),1)[0])))
    with (folder/'perfil.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['r_mm','Ez_real','Ez_imag','Hp_real','Hp_imag','Sr','Sr_anterior','Sr_r2','usado_ajuste'])
        w.writerows(zip(r,last['ez'].real,last['ez'].imag,last['hp'].real,last['hp'].imag,last['sr'],samples[-2]['sr'],p,mask.astype(int)))
    return dict(ajuste=fitted,ventanas=window,balance=[dict(t_M=s['t_M'],**s['balance']) for s in samples],
        dominio_anillo_mm=[lam,2*lam,.25*lam,1.25*lam],cambio_temporal=changes,
        cambio_temporal_perfil=relative_change(samples[-2]['sr'],last['sr']),estacionario=max(changes[-2:])<1e-4,
        geometria=dict(rmax_mm=rmax,zmax_mm=zmax,brazo_mm=arm,radio_mm=.2,gap_mm=gap),
        ventana_ajuste_lambda=[lo,4],muestra_negativa_en_ventana=int(np.sum((r>lo*lam)&(r<4*lam)&(p<=0))))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('tipo',choices=['plana','lamina','antena']);ap.add_argument('medio',choices=list(M))
    ap.add_argument('--res',type=int,required=True);ap.add_argument('--d',type=float,default=0);ap.add_argument('--pml',type=float,default=2)
    ap.add_argument('--validacion',action='store_true');ap.add_argument('--id',required=True);ap.add_argument('--destino',required=True)
    args=ap.parse_args();start=time.monotonic();mp.verbosity(0);folder=Path(args.destino);folder.mkdir(parents=True,exist_ok=True)
    eps,sigma=M[args.medio];alpha,lam,sd=theory(eps,sigma)
    config=dict(id=args.id,tipo=args.tipo,medio=args.medio,resolucion_px_mm=args.res,epsr=eps,sigma_eq_S_m=sigma,
        sigma_D_M=sd,frecuencia_Hz=F,epsilon0=EPS0,mu0=MU0,c=C,alpha_teoria_dB_mm=alpha,lambda_mm=lam,
        pml_factor=args.pml,fuente='CW suave, width=2T, slowness=6, compleja',Courant=.5,
        meep=mp.__version__,python=platform.python_version(),sistema=platform.platform(),hilos=1,
        inicio_UTC=datetime.now(timezone.utc).isoformat(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        materiales_sha256=hashlib.sha256((ROOT/'materiales.csv').read_bytes()).hexdigest())
    save_json(folder/'configuracion.json',config)
    result={'plana':homogeneous,'lamina':slab,'antena':antenna}[args.tipo](args,folder,eps,sigma,alpha,lam,sd)
    result.update(config);result.update(segundos=time.monotonic()-start,rss_max_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                                     fin_UTC=datetime.now(timezone.utc).isoformat(),completo=True)
    save_json(folder/'resultado.json',result)
    print(json.dumps(dict(id=args.id,segundos=result['segundos'],estacionario=result['estacionario']),ensure_ascii=False),flush=True)
