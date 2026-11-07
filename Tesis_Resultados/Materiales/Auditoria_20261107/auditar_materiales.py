"""Audita metadatos y cuantifica 70 frente a 78; no ejecuta ni modifica FDTD."""
from pathlib import Path
import json,urllib.request,urllib.parse,math,csv
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent;ROOT.mkdir(exist_ok=True)
queries={
 'hossain2026':'A Simulation-Based Computational Study on the Dielectric Response of Human Hand Tissues to Radiofrequency Radiation from Mobile Devices',
 'martinez2022':'Energy balance and radiation efficiency of dipole antennas in saltwater environments',
 'kim2025':'Complex permittivity measurements of standard building materials at sub-6 GHz bands for 5G indoor planning'}
results=[]
for key,title in queries.items():
    url='https://api.crossref.org/works?'+urllib.parse.urlencode({'query.title':title,'rows':3})
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'ThesisMaterialAudit/1.0'}),timeout=20) as response:
            data=json.load(response)['message']['items']
        results.append(dict(key=key,query=title,url=url,retrieved=datetime.now(timezone.utc).isoformat(),candidates=[{k:x.get(k) for k in ('title','author','DOI','container-title','published','volume','issue','page','article-number')} for x in data]))
    except Exception as e:results.append(dict(key=key,query=title,url=url,error=str(e)))
(ROOT/'metadatos_consultados.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
rows=[]
for epsr in (78.,70.):
    f=3e9;sig=4.;eps0=8.854e-12;mu0=4*math.pi*1e-7;omega=2*math.pi*f
    td=sig/(omega*eps0*epsr);s=math.sqrt(1+td*td);pref=omega*math.sqrt(mu0*eps0*epsr/2)
    alpha=pref*math.sqrt(td*td/(s+1));beta=pref*math.sqrt(s+1)
    rows.append(dict(epsr=epsr,sigma_S_m=sig,f_Hz=f,alpha_Np_m=alpha,alpha_dB_mm=20/math.log(10)*alpha/1000,lambda_mm=2*math.pi/beta*1000,profundidad_amplitud_mm=1000/alpha,
        discrepancia_pendiente_historica_pct=100*abs(.7012-20/math.log(10)*alpha/1000)/(20/math.log(10)*alpha/1000)))
with (ROOT/'sensibilidad_70_78.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
print(json.dumps(rows,indent=2));print('Cambio alpha (%)',100*(rows[1]['alpha_dB_mm']/rows[0]['alpha_dB_mm']-1))
for item in results:
    print(item['key'],[(r['title'],r['DOI']) for r in item.get('candidates',[])],item.get('error',''))
