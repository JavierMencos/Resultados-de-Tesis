"""Cola secuencial reanudable desde VS Code/WSL; sin credenciales ni acceso a cuotas.

Crear PAUSAR en esta carpeta detiene la cola después del caso actual.
Una interrupción conserva todos los casos terminados; el caso interrumpido
se vuelve a ejecutar en un directorio de intento nuevo al reanudar.
"""
import argparse, csv, fcntl, hashlib, json, os, platform, resource, signal, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent


def write(p,data):
    tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8');tmp.replace(p)


def memory():
    values={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines()}
    return values['MemAvailable']


def plan():
    jobs=[]
    def add(tipo,medio,res,d=0,pml=2,validacion=False):
        ident=f'{tipo}_{medio}_{res}px'+(f'_{d:g}mm' if d else '')+(f'_pml{pml}' if pml!=2 else '')
        jobs.append(dict(id=ident,tipo=tipo,medio=medio,res=res,d=d,pml=pml,validacion=validacion))
    for m in ('vacio','concreto','agua_salada','tejido_muscular'):
        for res in (5,10):add('plana',m,res)
    for m in ('concreto','agua_salada','tejido_muscular'):
        for d in ((10,20,40,30) if m=='concreto' else (2,5,10,7)):
            for res in (5,10,20):add('lamina',m,res,d,validacion=d in (30,7))
        add('lamina',m,10,20 if m=='concreto' else 5,pml=3)
    for res in (5,10):add('lamina','vacio',res,10)
    # Agua/músculo primero: control de los casos cortos antes de las mallas costosas.
    for m in ('agua_salada','tejido_muscular','concreto','vacio'):add('antena',m,5)
    for res in (10,20,40):add('antena','agua_salada',res)
    for res in (10,20):add('antena','tejido_muscular',res)
    add('antena','concreto',10)
    for m in ('agua_salada','tejido_muscular','concreto'):add('antena',m,5,pml=3)
    return jobs


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--solo',choices=['pruebas','completa'],default='completa');args=ap.parse_args()
    lock=(ROOT/'campana.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    os.nice(15)
    jobs=plan();write(ROOT/'plan.json',jobs)
    expected=hashlib.sha256((ROOT/'simular.py').read_bytes()).hexdigest()
    materials=hashlib.sha256((ROOT/'materiales.csv').read_bytes()).hexdigest()
    write(ROOT/'entorno.json',dict(python=sys.version,sistema=platform.platform(),cpu=Path('/proc/cpuinfo').read_text().split('model name')[1].split('\n')[0],
          memoria=Path('/proc/meminfo').read_text(),hilos=1,nice=15,rss_limite_GiB=5.0,reserva_memoria_MiB=700,
          nota='Un trabajo a la vez. No se modifica la configuración global de WSL.'))
    state=dict(inicio_UTC=datetime.now(timezone.utc).isoformat(),estado='en_curso',completadas=[],total=len(jobs))
    for job in jobs:
        if args.solo=='pruebas' and job['tipo']=='antena':break
        if (ROOT/'PAUSAR').exists():state['estado']='pausa_solicitada';break
        directory=ROOT/'corridas'/job['id'];directory.mkdir(parents=True,exist_ok=True)
        previous=[]
        for f in directory.glob('*/resultado.json'):
            r=json.loads(f.read_text())
            accepted=r.get('completo') and r.get('estacionario')
            if job['tipo']=='plana' and r.get('alpha_teoria_dB_mm',0)>0:
                accepted=accepted and abs(r.get('discrepancia_teoria_dB_mm',float('inf')))/r['alpha_teoria_dB_mm']<=.01
            if accepted and r.get('script_sha256')==expected and r.get('materiales_sha256')==materials:previous.append(f)
        if previous:state['completadas'].append(job['id']);continue
        if memory()<1.2*1024**3:state.update(estado='pausa_memoria',pendiente=job['id']);break
        attempt=directory/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');attempt.mkdir()
        cmd=[sys.executable,'-u',str(ROOT/'simular.py'),job['tipo'],job['medio'],'--res',str(job['res']),
             '--d',str(job['d']),'--pml',str(job['pml']),'--id',job['id'],'--destino',str(attempt)]
        if job['validacion']:cmd.append('--validacion')
        env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        start=time.monotonic();error=None;peak=0
        def limits():resource.setrlimit(resource.RLIMIT_AS,(7*1024**3,7*1024**3))
        with (attempt/'ejecucion.log').open('w') as log:
            child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,preexec_fn=limits)
            try:
                while child.poll() is None:
                    status=Path(f'/proc/{child.pid}/status')
                    try:
                        rss=next((int(l.split()[1])*1024 for l in status.read_text().splitlines() if l.startswith('VmRSS:')),0)
                    except FileNotFoundError:rss=0
                    peak=max(peak,rss)
                    state.update(actual=job['id'],pid=child.pid,segundos_actual=time.monotonic()-start,rss_MiB=rss/1024**2,
                                 actualizacion_UTC=datetime.now(timezone.utc).isoformat())
                    write(ROOT/'estado.json',state)
                    if rss>5*1024**3 or memory()<700*1024**2:
                        error='limite_memoria';child.terminate()
                        try:child.wait(timeout=15)
                        except subprocess.TimeoutExpired:child.kill();child.wait()
                        break
                    time.sleep(30 if job['tipo']=='antena' else 1)
            except BaseException:
                child.terminate();child.wait();raise
        write(attempt/'proceso.json',dict(comando=cmd,retorno=child.returncode,segundos=time.monotonic()-start,
                                        rss_observada_max_MiB=peak/1024**2,error=error))
        if child.returncode!=0 or not (attempt/'resultado.json').exists():
            state.update(estado='requiere_revision',fallida=job['id'],motivo=error or 'proceso_fallido');break
        result=json.loads((attempt/'resultado.json').read_text())
        state['completadas'].append(job['id'])
        if not result['estacionario']:
            state.update(estado='requiere_revision',fallida=job['id'],motivo='sin_estacionariedad');break
        if job['tipo']=='plana' and result['alpha_teoria_dB_mm']>0 and result['discrepancia_teoria_dB_mm']/result['alpha_teoria_dB_mm']>.01:
            state.update(estado='requiere_revision',fallida=job['id'],motivo='error_planar_superior_1pct');break
    else:state['estado']='finalizada'
    if args.solo=='pruebas' and state['estado']=='en_curso':state['estado']='pruebas_finalizadas'
    state['fin_turno_UTC']=datetime.now(timezone.utc).isoformat();write(ROOT/'estado.json',state)
    print(json.dumps(state,indent=2,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
