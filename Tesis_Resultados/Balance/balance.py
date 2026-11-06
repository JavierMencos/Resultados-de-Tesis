"""Corrida independiente del balance en un volumen anular de dieléctrico."""
import argparse
import json
import platform
import resource
import time
from pathlib import Path
from datetime import datetime, timezone
inicio = time.monotonic()
parser = argparse.ArgumentParser()
parser.add_argument("medio", choices=["vacio","concreto","agua_salada","tejido_muscular"])
parser.add_argument("--resolucion", type=int, default=5)
parser.add_argument("--prueba", action="store_true", help="Arranque corto; excluido de los resultados físicos")
args = parser.parse_args()
if args.resolucion < 1:
    parser.error("La resolución debe ser positiva")
import meep as mp
import numpy as np

# =====================================================================
# 1. PARÁMETROS FÍSICOS Y DICCIONARIO DE MATERIALES
# =====================================================================
FRECUENCIA_HZ = 3.0e9
C_VACIO = 299792458.0
EPS0 = 8.854e-12
MU0 = 4 * np.pi * 1e-7
LAMBDA_0_MM = (C_VACIO / FRECUENCIA_HZ) * 1e3
OMEGA = 2 * np.pi * FRECUENCIA_HZ

# Diccionario ABIERTO: para agregar un material nuevo, basta con una
# entrada {"eps": ..., "sigma": ...} (valores "snapshot" a la frecuencia
# de trabajo; ver nota final sobre modelos dispersivos si en el futuro
# se simula un barrido de frecuencia en vez de una sola frecuencia fija).
propiedades_materiales = {
    "vacio":           {"eps": 1.0,  "sigma": 0.0},
    "concreto":        {"eps": 4.5,  "sigma": 0.05},
    "agua_salada":     {"eps": 78.0, "sigma": 4.0},
    "tejido_muscular": {"eps": 52.7, "sigma": 2.2},
}

# --- SELECCIÓN ACTIVA DEL MEDIO ---
nombre_medio = args.medio  # Cambiar para generar cada una de tus gráficas

eps_actual = propiedades_materiales[nombre_medio]["eps"]
sigma_actual = propiedades_materiales[nombre_medio]["sigma"]


def calc_meep_conductivity(sigma_S_m, epsilon_r, a_mm=1.0):
    """Convierte conductividad física (S/m) a la conductividad-D que espera
    MEEP en sus unidades naturales (Cap. 7, definición de materiales)."""
    factor = (a_mm * 1e-3) / (EPS0 * C_VACIO)
    return (sigma_S_m * factor) / epsilon_r if epsilon_r != 0 else 0.0


def tan_delta(sigma_S_m, epsilon_r, omega=OMEGA):
    """Tangente de pérdidas, Cap. 2.5. Es la magnitud correcta para
    clasificar un medio -- no la conductividad cruda, que depende
    también de eps_r."""
    if sigma_S_m == 0 or epsilon_r == 0:
        return 0.0
    return sigma_S_m / (omega * epsilon_r * EPS0)


def alpha_beta_exacto(sigma_S_m, epsilon_r, omega=OMEGA):
    """alpha (Np/m) y beta (rad/m) exactos del medio con pérdidas (Cap.
    2.5), en forma numéricamente estable: sqrt(1+x^2)-1 = x^2/(sqrt(1+x^2)+1)
    -- evita cancelación catastrófica cuando tan_delta es muy pequeño
    (medios de muy baja pérdida, o el vacío). Se reduce exactamente al
    caso ideal (alpha=0, beta=omega*sqrt(mu*eps)) cuando sigma=0, sin
    necesitar ningún caso especial."""
    eps = epsilon_r * EPS0
    td = tan_delta(sigma_S_m, epsilon_r, omega)
    pref = omega * np.sqrt(MU0 * eps / 2.0)
    s = np.sqrt(1.0 + td ** 2)
    alpha = pref * np.sqrt(td ** 2 / (s + 1.0)) if td > 0 else 0.0
    beta = pref * np.sqrt(s + 1.0)
    return alpha, beta


tan_delta_actual = tan_delta(sigma_actual, eps_actual)
alpha_teorico_Np_m, beta_teorico = alpha_beta_exacto(sigma_actual, eps_actual)
alpha_teorico_dB_mm = alpha_teorico_Np_m * 8.686 / 1000.0

medio_actual = mp.Medium(epsilon=eps_actual, D_conductivity=calc_meep_conductivity(sigma_actual, eps_actual))

# lambda_medio viene de beta (fase real con pérdidas, Cap. 2.5) -- válido
# automáticamente para cualquier material, incluido el vacío.
lambda_medio = (2 * np.pi / beta_teorico) * 1e3

print(f"[{nombre_medio.upper()}] tan(delta)={tan_delta_actual:.4f} | "
      f"alpha_teorico={alpha_teorico_Np_m:.3f} Np/m ({alpha_teorico_dB_mm:.4f} dB/mm) | "
      f"lambda_medio={lambda_medio:.3f} mm")

# =====================================================================
# 2. ESCALADO GEOMÉTRICO Y FRONTERAS (AJUSTE UNIVERSAL, tal como lo dejaste)
# =====================================================================
R_max = 5.0 * lambda_medio
grosor_pml = 2.0 * lambda_medio  # Grosor duplicado para absorber rebotes (vital para el vacío)

L_antena = lambda_medio / 2.0
espacio_libre_z = 2.0 * lambda_medio
Z_max = L_antena + (2.0 * espacio_libre_z) + (2.0 * grosor_pml)
cell = mp.Vector3(R_max + grosor_pml, 0, Z_max)

# AVISO (sin cambios de tu versión): 1.0 es la frontera "dieléctrico /
# buen conductor" del Cap. 2.5, usada aquí como heurística razonable --
# no verificada contra la documentación interna de MEEP.
if tan_delta_actual > 1.0:
    pml_layers = [mp.Absorber(thickness=grosor_pml, direction=mp.R), mp.Absorber(thickness=grosor_pml, direction=mp.Z)]
    tipo_frontera = "Absorber (Grosor Extendido 2λ)"
else:
    pml_layers = [mp.PML(thickness=grosor_pml, direction=mp.R), mp.PML(thickness=grosor_pml, direction=mp.Z)]
    tipo_frontera = "PML (Grosor Extendido 2λ)"

# =====================================================================
resolution = args.resolucion

# 3. ANTENA MARCONI Y RELOJ FDTD
# =====================================================================
gap = 0.4
if gap >= (L_antena / 2.0):
    gap = L_antena / 10.0
altura_brazo = (L_antena - gap) / 2
posicion_centro_brazo = (gap / 2.0) + (altura_brazo / 2.0)

geometry = [
    mp.Block(material=mp.metal, center=mp.Vector3(R_max / 2, 0, -Z_max / 2 - (gap / 2.0)),
             size=mp.Vector3(mp.inf, 0, Z_max)),
    mp.Cylinder(material=mp.metal, radius=0.2, height=altura_brazo,
                center=mp.Vector3(0, 0, posicion_centro_brazo))
]

sources = [mp.Source(mp.ContinuousSource(frequency=1.0 / LAMBDA_0_MM, is_integrated=True),
                      component=mp.Ez, center=mp.Vector3(0, 0, 0), size=mp.Vector3(0.4, 0, gap))]

sim = mp.Simulation(cell_size=cell, boundary_layers=pml_layers, geometry=geometry, sources=sources,
                     resolution=resolution, default_material=medio_actual, dimensions=mp.CYLINDRICAL, m=0,
                     eps_averaging=True, force_complex_fields=True)

# Tiempo dinámico basado en atenuación del medio (tal como lo dejaste).
# AVISO para medios de pérdida muy baja / vacío exacto: más tiempo
# ayuda a alcanzar un estado verdaderamente estacionario, pero NO reduce
# la amplitud de una reflexión residual cuando alpha=0 -- solo una PML
# más gruesa hace eso (Sec. 6.10/7.12).
tiempo_vuelo = R_max * np.sqrt(eps_actual)
if tan_delta_actual < 0.1:
    tiempo_estacionario = (3.0 * tiempo_vuelo) + (20.0 * LAMBDA_0_MM)   # Vacío/Concreto (3 rebotes)
else:
    tiempo_estacionario = (1.5 * tiempo_vuelo) + (10.0 * LAMBDA_0_MM)   # Agua/Músculo (1.5 rebotes)

# Volumen anular homogéneo, sin fuentes, alejado del conductor y de la PML.
muestras = []
def medir(sim):
    # Muestreo explícito en coordenadas físicas, incluidas las cuatro caras.
    n = int(np.ceil(lambda_medio * resolution)) + 1
    r = np.linspace(lambda_medio, 2*lambda_medio, n)
    z = np.linspace(0.25*lambda_medio, 1.25*lambda_medio, n)
    er, ez, hp = np.empty((3,n,n), dtype=complex)
    for i, radio in enumerate(r):
        for j, altura in enumerate(z):
            punto = mp.Vector3(radio, 0, altura)
            er[i,j], ez[i,j], hp[i,j] = (
                sim.get_field_point(c, punto) for c in (mp.Er, mp.Ez, mp.Hp))
    sr = -0.5*np.real(ez*np.conj(hp))
    sz = 0.5*np.real(er*np.conj(hp))
    area = 2*np.pi*r
    integrar = np.trapezoid
    entrada = area[0]*integrar(sr[0], z)
    exterior = area[-1]*integrar(sr[-1], z)
    tapa_sup = integrar(area*sz[:,-1], r)
    tapa_inf = -integrar(area*sz[:,0], r)
    sigma_meep = eps_actual * calc_meep_conductivity(sigma_actual, eps_actual)
    joule = 0.5*sigma_meep*(abs(er)**2 + abs(ez)**2)
    perdida = integrar(area*integrar(joule, z, axis=1), r)
    residuo = entrada-exterior-tapa_sup-tapa_inf-perdida
    muestras.append(dict(t=sim.meep_time(), dominio_mm=[r[0],r[-1],z[0],z[-1]],
        interior=entrada, exterior=exterior, tapa_superior=tapa_sup, tapa_inferior=tapa_inf,
        joule=perdida, residuo=residuo, residuo_relativo=residuo/abs(entrada) if entrada else None))

duracion = 1.5*LAMBDA_0_MM if args.prueba else tiempo_estacionario
for dur in (duracion, 1.0 if args.prueba else LAMBDA_0_MM):
    sim.run(mp.at_end(mp.synchronized_magnetic(medir)), until=dur)
registro = dict(medio=args.medio, px_mm=resolution, prueba=args.prueba, unidades="Meep",
    meep=mp.__version__, sistema=platform.platform(), segundos=time.monotonic()-inicio,
    rss_max_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, muestras=muestras)
destino=Path(__file__).resolve().parent/"corridas"
destino.mkdir(exist_ok=True)
marca=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
archivo=destino/f"{args.medio}_{resolution}px_{'prueba' if args.prueba else 'balance'}_{marca}.json"
archivo.write_text(json.dumps(registro,indent=2, allow_nan=False), encoding="utf-8")
print(archivo)


