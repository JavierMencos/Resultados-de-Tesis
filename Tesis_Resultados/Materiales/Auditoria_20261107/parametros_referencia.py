"""Contraste documental a 3 GHz; no modifica ni ejecuta las simulaciones históricas.

Python >=3.9, biblioteca estándar. Ejecutar: python parametros_referencia.py
Descarga únicamente la base de datos pública IT'IS V5.0 (datos, no ejecutables).
UIT P.527-6, ecuaciones 5-27; UIT P.2040-4, ecuaciones 57-58 y cuadro 3.
La comparación usa parámetros de referencia, no mediciones propias ni incertidumbres.
"""
from pathlib import Path
import csv
import hashlib
import io
import json
import math
import platform
import time
import urllib.request
import zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
EPS0 = 8.8541878128e-12
MU0 = 1.25663706212e-6
URL_ITIS = 'https://itis.swiss/assets/Downloads/TissueDb/Database-V5-0.zip'
F = 3e9


def agua_uit(f_ghz, temperatura=20., salinidad=35.):
    """P.527-6: eps' - j eps'', convención exp(+j omega t).

    Se conserva literalmente el factor redondeado 18 de la ecuación 16.
    sigma_equivalente = omega*epsilon0*eps'' incluye todas las pérdidas.
    """
    t, s, f = temperatura, salinidad, f_ghz
    if not (-4 <= t <= 40 and 0 <= s <= 40 and f > 0):
        raise ValueError('Fuera de las condiciones de aplicación implementadas')
    theta = 300/(t+273.15)-1
    es = 77.66+103.3*theta
    e1, einf = .0671*es, 3.52-7.52*theta
    f1 = 20.20-146.4*theta+316*theta**2
    f2 = 39.8*f1
    ess = es*math.exp(-3.33330e-3*s+4.74868e-6*s*s)
    f1s = f1*(1+s*(2.3232e-3-7.9208e-5*t+3.6764e-6*t*t
                   +3.5594e-7*t**3+8.9795e-9*t**4))
    e1s = e1*math.exp(-6.28908e-3*s+1.76032e-4*s*s-9.22144e-5*t*s)
    f2s = f2*(1+s*(-1.99723e-2+1.81176e-4*t))
    einfs = einf*(1+s*(-2.04265e-3+1.57883e-4*t))
    sigma35 = 2.903602+8.607e-2*t+4.738817e-4*t*t-2.991e-6*t**3+4.3047e-9*t**4
    r15 = s*(37.5109+5.45216*s+1.4409e-2*s*s)/(1004.75+182.283*s+s*s)
    a0 = (6.9431+3.2841*s-9.9486e-2*s*s)/(84.850+69.024*s+s*s)
    a1 = 49.843-.2276*s+.198e-2*s*s
    sigma_ionica = sigma35*r15*(1+a0*(t-15)/(a1+t))
    x, y = f/f1s, f/f2s
    real = (ess-e1s)/(1+x*x)+(e1s-einfs)/(1+y*y)+einfs
    loss = x*(ess-e1s)/(1+x*x)+y*(e1s-einfs)/(1+y*y)+18*sigma_ionica/f
    return real, 2*math.pi*f*1e9*EPS0*loss, sigma_ionica, loss


def musculo_itis():
    archive = ROOT/'cache'/'Database-V5-0.zip'
    archive.parent.mkdir(exist_ok=True)
    if not archive.exists():
        with urllib.request.urlopen(URL_ITIS, timeout=60) as response:
            archive.write_bytes(response.read())
    with zipfile.ZipFile(archive) as z:
        name = next(n for n in z.namelist() if n.startswith('Thermal_dielectric') and n.endswith('(ASCII).txt'))
        raw = z.read(name)
    # El archivo ASCII del distribuidor usa caracteres Latin-1 (grado y micro).
    text = raw.decode('latin-1')
    records = list(csv.reader(io.StringIO(text), delimiter='\t'))
    header = next(r for r in records if 'tau1 (ps)' in r)
    row = next(r for r in records if len(r)>1 and r[1]=='Muscle')
    keys = ['ef','del1','tau1 (ps)','alf1','del2','tau2 (ns)','alf2',
            'sig','del3','tau3 (µs)','alf3','del4','tau4 (ms)','alf4']
    coeff = {k: float(row[header.index(k)]) for k in keys}
    value = complex(coeff['ef'], -coeff['sig']/(2*math.pi*F*EPS0))
    for i, unit, scale in [(1,'ps',1e-12),(2,'ns',1e-9),(3,'µs',1e-6),(4,'ms',1e-3)]:
        value += coeff[f'del{i}']/(1+(1j*2*math.pi*F*coeff[f'tau{i} ({unit})']*scale)**(1-coeff[f'alf{i}']))
    evidence = dict(url=URL_ITIS, doi='10.13099/VIP21000-05-0', file=name,
                    archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                    data_sha256=hashlib.sha256(raw).hexdigest(), tissue='Muscle',
                    coefficients=coeff, model='Gabriel; tabla principal, no Alternative Dielectrics')
    return value.real, -value.imag*2*math.pi*F*EPS0, evidence


def alpha(eps, sigma):
    q = sigma/(2*math.pi*F*EPS0*eps)
    return 2*math.pi*F*math.sqrt(MU0*EPS0*eps/2)*q/math.sqrt(math.sqrt(1+q*q)+1)*20/math.log(10)/1000


def main():
    start = time.monotonic()
    muscle_e, muscle_s, evidence = musculo_itis()
    water_e, water_s, water_ionic, loss = agua_uit(3)
    # Prueba física independiente: con S=0 debe recuperarse el modelo de agua pura.
    theta = 300/293.15-1
    es = 77.66+103.3*theta; e1=.0671*es; einf=3.52-7.52*theta
    f1=20.20-146.4*theta+316*theta**2
    pure = (es-e1)/(1+1j*3/f1)+(e1-einf)/(1+1j*3/(39.8*f1))+einf
    pure_calc=agua_uit(3,20,0)
    assert abs(pure_calc[0]-pure.real)<1e-10
    assert abs(pure_calc[3]+pure.imag)<1e-10 and pure_calc[2]==0
    assert alpha(1,0)==0 and water_s>water_ionic>0 and muscle_s>0
    values = [
        ('vacio',1.,0.,1.,0.,'Definicion del vacio ideal'),
        ('concreto',4.5,.05,5.24,.0462*3**.7822,'UIT-R P.2040-4, cuadro 3; 1-100 GHz'),
        ('agua_salada',78.,4.,water_e,water_s,'UIT-R P.527-6; 20 C, 35 g/kg; condiciones de referencia elegidas'),
        ('tejido_muscular',52.7,2.2,muscle_e,muscle_s,'ITIS V5.0; dispersion Gabriel; Muscle')]
    rows = []
    for medium, eh, sh, er, sr, source in values:
        rows.append(dict(medio=medium, f_Hz=F, eps_historica=eh, sigma_historica_S_m=sh,
                         eps_referencia=er, sigma_equivalente_referencia_S_m=sr,
                         alpha_historica_teorica_dB_mm=alpha(eh,sh),
                         alpha_referencia_teorica_dB_mm=alpha(er,sr),
                         cambio_alpha_pct=100*(alpha(er,sr)/alpha(eh,sh)-1) if sh else '',
                         fuente=source))
    with (ROOT/'comparacion_parametros_3GHz.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=rows[0]); writer.writeheader();writer.writerows(rows)
    metadata=dict(fecha_UTC=datetime.now(timezone.utc).isoformat(),python=platform.python_version(),
                  segundos=time.monotonic()-start, eps0=EPS0,mu0=MU0,itis=evidence,
                  agua=dict(temperatura_C=20,salinidad_g_kg=35,sigma_ionica_S_m=water_ionic,
                            epsilon_perdida=loss,factor_redondeado_ec16=18),
                  verificacion='limite S=0 contra Debye puro; pasividad; vacio sin atenuacion',
                  incertidumbre='No estimada: son evaluaciones deterministas de modelos publicados.',
                  nota='Las constantes SI difieren ligeramente de las redondeadas en las corridas históricas; no sustituir sus referencias teóricas archivadas.')
    (ROOT/'procedencia_y_ejecucion.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(rows,indent=2,ensure_ascii=False))
    print('sigma ionica agua:',water_ionic,'S/m; pruebas: OK')


if __name__=='__main__':
    main()
