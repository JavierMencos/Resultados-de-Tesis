"""
Simulación FDTD - Fase 2: monopolo Marconi en medios complejos.
================================================================
Capa de METODOLOGÍA/implementación (distinta del marco teórico ya
redactado). Cada bloque referencia el capítulo/sección del marco
teórico del que se deriva, para trazabilidad completa.

DISEÑO GENERAL: para simular un material nuevo, agregue una entrada al
diccionario `propiedades_materiales` con sus valores de eps y sigma (a
la frecuencia de trabajo). TODO lo demás -- lambda_medio, geometría de
la antena, tipo de frontera, tiempo de simulación y el modelo
estadístico de ajuste -- se deriva automáticamente de esos dos números
vía tan(delta). Ninguna rama de código depende del *nombre* del
material.

Respecto a la versión anterior de esta sesión, se conservan tus mejoras
de velocidad (R_max=5*lambda, grosor_pml=2*lambda fijo, resolución
híbrida, tiempo de establecimiento por "rebotes") y se corrigen dos
puntos:

  1. NO se elimina la prueba de Durbin-Watson de la salida. Se reporta
     SIEMPRE como diagnóstico de estructura residual, separado de la
     etiqueta de "ajuste utilizable" (R²/RMSE) -- así se puede seguir
     usando alpha_app con confianza cuando el error vs. teoría es
     pequeño, sin esconder que hay estructura fina sin modelar (que,
     como vimos, es un efecto real y pequeño de campo cercano/reflexión
     residual, Cap. 4.6/8, no un fallo del modelo físico).
  2. Se repone la restricción física alpha_db >= 0 en M0 y M1 (ya la
     tenía M2): el teorema de Poynting (Cap. 3) prohíbe que un medio
     pasivo amplifique la señal.

Se añade además un barrido automático de sensibilidad de limite_inf
(usando los mismos datos, sin volver a correr MEEP) para verificar si
el alpha_app es estable al alejar la ventana de ajuste de la antena.

NOTA para "vacio": alpha_teorico=0 exactamente. El perfil compensado
por r^2 debería verse PLANO; cualquier ondulación es 100% artefacto de
frontera (no hay pérdida material que la explique). Más tiempo de
simulación ayuda a alcanzar un estado verdaderamente estacionario, pero
NO reduce la amplitud de esa contaminación en un medio sin pérdidas --
solo una PML más gruesa/mejor lo hace.
"""

import meep as mp
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy.optimize import curve_fit
from scipy import stats as scipy_stats
import os

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
nombre_medio = "concreto"  # Cambiar para generar cada una de tus gráficas

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
# RESOLUCIÓN DINÁMICA HÍBRIDA (Física + Geométrica) -- tal como la dejaste
# =====================================================================
res_fisica = 30.0 / lambda_medio       # 30 px/lambda (precisión de fase, Cap. 6.9)
res_geometrica = 20.0                   # mínimo 5 px/mm para no perder la estructura del monopolo
resolution = int(np.ceil(max(res_fisica, res_geometrica)))

# Transparencia: con estos 4 materiales, res_geometrica siempre domina
# (resolution=5 px/mm), lo que deja el radio del monopolo (0.2mm) en
# solo ~2 píxeles. eps_averaging=True (abajo) mitiga parte del error de
# escalón, pero no lo elimina. Se imprime explícitamente para que quede
# visible en cada corrida, no oculto:
px_diametro_monopolo = round(2 * 0.2 * resolution, 1)
print(f"[{nombre_medio.upper()}] Frontera: {tipo_frontera} | resolution={resolution} px/mm "
      f"(~{px_diametro_monopolo:.0f} px a través del diámetro del monopolo -- si vas a usar "
      f"la impedancia de entrada o el campo muy cercano, valide con una corrida a resolución "
      f"mayor antes de confiar en ese resultado)")

# =====================================================================
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

sim.run(until=tiempo_estacionario)

# =====================================================================
# 4. EXTRACCIÓN DEL VECTOR DE POYNTING PROMEDIADO
# =====================================================================
line_size, line_center = mp.Vector3(R_max, 0, 0), mp.Vector3(R_max / 2, 0, 0)
ez_data = sim.get_array(center=line_center, size=line_size, component=mp.Ez)
hphi_data = sim.get_array(center=line_center, size=line_size, component=mp.Hp)

# S_r = -0.5*Re(Ez * Hphi*) porque z_hat x phi_hat = -r_hat (Cap. 3.6)
intensidad_poynting = -0.5 * np.real(ez_data * np.conjugate(hphi_data))
r_coords = np.linspace(0, R_max, len(intensidad_poynting))

# Compensación geométrica por r^2 (no por r), Cap. 2.5 + 3.9
potencia_compensada = np.abs(intensidad_poynting) * (r_coords ** 2 + 1e-9)
intensidad_db = 10 * np.log10(potencia_compensada + 1e-20)

# =====================================================================
# 5. SELECCIÓN DE MODELO POR AIC + DIAGNÓSTICO DE RESIDUOS
# =====================================================================
# Evadir la zona reactiva de manera proporcional al material (tal como
# lo dejaste) -- se amplía más abajo con un barrido de sensibilidad.
limite_inf = 2.0 * lambda_medio if tan_delta_actual > 0.2 else 1.5 * lambda_medio
limite_sup = R_max - (1.0 * lambda_medio)   # protege contra contaminación de la pared PML
UMBRAL_RUIDO_DB, UMBRAL_DELTA_AIC = -80, 10.0
DW_MIN, DW_MAX = 1.5, 2.5   # rango "sin autocorrelación", verificado con datos sintéticos

mascara = (r_coords > limite_inf) & (r_coords < limite_sup) & (intensidad_db > UMBRAL_RUIDO_DB)
r_seguro = r_coords[mascara]
db_seguro = intensidad_db[mascara]


def modelo_M0(r, A, alfa_db):
    return A - alfa_db * r


def modelo_M1(r, A, alfa_db, B, beta, phi):
    return A - alfa_db * r + B * np.sin(beta * r + phi)


def modelo_M2(r, A, alfa_db, C):
    return A - alfa_db * r - C * np.log10(r)


# Restricción física común a los tres modelos (Cap. 3, teorema de
# Poynting): un medio pasivo no puede amplificar la señal, alfa_db >= 0.
# (Antes solo M2 la tenía; se repone para M0 y M1.)
BOUNDS_M0 = ([-np.inf, 0.0], [np.inf, np.inf])
BOUNDS_M1 = ([-np.inf, 0.0, -np.inf, 0.0, -np.inf], [np.inf, np.inf, np.inf, np.inf, np.inf])
BOUNDS_M2 = ([-np.inf, 0.0, 0.0], [np.inf, np.inf, np.inf])


def ajustar_modelo(func, r, db, p0, bounds, k_params):
    try:
        popt, pcov = curve_fit(func, r, db, p0=p0, bounds=bounds, maxfev=20000)
        residuos = db - func(r, *popt)
        n = len(db)
        rss = np.sum(residuos ** 2)
        aic = 2 * k_params + n * np.log(rss / n) if rss > 0 else -np.inf
        return {"popt": popt, "pcov": pcov, "residuos": residuos, "aic": aic}
    except Exception:
        return None


def bootstrap_bloques_moviles(r, residuos, modelo, popt0, bounds, n_boot=2000, block_len=None, seed=0):
    """Bootstrap por bloques móviles (Künsch, 1989; Politis y Romano, 1994)
    sobre los residuos del ajuste ganador. A diferencia de un bootstrap de
    residuos i.i.d., preserva la autocorrelación real de los residuos
    (que ya sabemos que existe, vía Durbin-Watson) muestreando bloques
    consecutivos en vez de puntos sueltos -- así el CI resultante no
    subestima la incertidumbre cuando hay estructura sistemática.
    Devuelve la distribución bootstrap de alpha_db y su CI percentil 95%.
    """
    rng = np.random.default_rng(seed)
    n = len(residuos)
    if block_len is None:
        block_len = max(5, int(round(n ** (1 / 3))))  # regla estándar (Hall et al., 1995)
    n_blocks = int(np.ceil(n / block_len))
    max_start = max(1, n - block_len)
    linea_base = modelo(r, *popt0)

    alphas_boot = []
    for _ in range(n_boot):
        starts = rng.integers(0, max_start, size=n_blocks)
        res_boot = np.concatenate([residuos[s:s + block_len] for s in starts])[:n]
        db_boot = linea_base + res_boot
        try:
            popt_b, _ = curve_fit(modelo, r, db_boot, p0=popt0, bounds=bounds, maxfev=20000)
            alphas_boot.append(popt_b[1])
        except Exception:
            continue

    alphas_boot = np.array(alphas_boot)
    if len(alphas_boot) < 50:
        return alphas_boot, (np.nan, np.nan), block_len
    ci = np.percentile(alphas_boot, [2.5, 97.5])
    return alphas_boot, ci, block_len


distancia_corte = None
resultados_sensibilidad = []

if len(r_seguro) > 20:
    slope, intercept = np.polyfit(r_seguro, db_seguro, 1)
    beta_guess = 2 * np.pi / (lambda_medio / 2.0)

    candidatos = {
        "M0": ajustar_modelo(modelo_M0, r_seguro, db_seguro,
                              p0=[intercept, max(abs(slope), 1e-6)], bounds=BOUNDS_M0, k_params=2),
        "M1": ajustar_modelo(modelo_M1, r_seguro, db_seguro,
                              p0=[intercept, max(abs(slope), 1e-6), 1.0, beta_guess, 0.0],
                              bounds=BOUNDS_M1, k_params=5),
        "M2": ajustar_modelo(modelo_M2, r_seguro, db_seguro,
                              p0=[intercept, max(abs(slope), 1e-6), 1.0], bounds=BOUNDS_M2, k_params=3),
    }
    validos = {k: v for k, v in candidatos.items() if v is not None}

    if not validos:
        distancia_corte, eq_texto, validez, nombre_modelo = R_max, "Error Conv.", "INVÁLIDO", "Ninguno"
        r_cuadrado = rmse = durbin_watson = alfa_real = 0
        estructura_residual = "N/A"
    else:
        nombre_modelo = "M0" if "M0" in validos else min(validos, key=lambda k: validos[k]["aic"])
        if "M0" in validos:
            for n, d in validos.items():
                if n != "M0" and (validos["M0"]["aic"] - d["aic"]) > UMBRAL_DELTA_AIC:
                    if nombre_modelo == "M0" or d["aic"] < validos[nombre_modelo]["aic"]:
                        nombre_modelo = n

        popt, residuos = validos[nombre_modelo]["popt"], validos[nombre_modelo]["residuos"]
        alfa_real = popt[1]
        linea_predicha = {"M0": modelo_M0, "M1": modelo_M1, "M2": modelo_M2}[nombre_modelo](r_seguro, *popt)
        eq_texto = f"{nombre_modelo}: $\\alpha_{{app}}={alfa_real:.4f}$ dB/mm"

        print("\n--- REPORTE DE EXTRACCIÓN FDTD ---")
        print("  AIC por modelo: " + ", ".join(f"{k}={v['aic']:.1f}" for k, v in validos.items()))
        print(f"  Modelo seleccionado (parsimonia, Delta-AIC>{UMBRAL_DELTA_AIC}): {nombre_modelo}")
        if alpha_teorico_dB_mm > 1e-9:
            error_relativo = 100 * (alfa_real - alpha_teorico_dB_mm) / alpha_teorico_dB_mm
            print(f"  alpha_app={alfa_real:.4f} dB/mm  vs  alpha_teorico={alpha_teorico_dB_mm:.4f} dB/mm  "
                  f"(diferencia {error_relativo:.2f}%)")
        else:
            print(f"  alpha_app={alfa_real:.4f} dB/mm  vs  alpha_teorico=0 (vacío: se espera perfil PLANO; "
                  f"cualquier alfa_app/ripple aquí es artefacto de frontera, no física de material)")

        # --- Auditoría estadística ---
        ss_res, ss_tot = np.sum(residuos ** 2), np.sum((db_seguro - np.mean(db_seguro)) ** 2)
        r_cuadrado = 1 - (ss_res / ss_tot) if ss_tot else 0
        rmse = np.sqrt(np.mean(residuos ** 2))
        durbin_watson = np.sum(np.diff(residuos) ** 2) / np.sum(residuos ** 2) if np.sum(residuos ** 2) else 0

        # Regla de "ajuste utilizable": R² y RMSE (criterio práctico de
        # esta tesis para decidir si alpha_app es confiable).
        validez = "VÁLIDO" if (r_cuadrado > 0.85 and rmse < 0.5) else "INVÁLIDO"

        # Diagnóstico de Durbin-Watson: NUNCA se omite, se reporta
        # siempre por separado. No decide "válido/inválido" por sí solo,
        # pero se imprime y se grafica -- si señala estructura, se
        # investiga (ventana de ajuste, campo cercano, reflexión
        # residual, Cap. 4.6/8), no se oculta.
        if DW_MIN < durbin_watson < DW_MAX:
            estructura_residual = "sin estructura sistemática detectable"
        else:
            estructura_residual = ("ESTRUCTURA SISTEMÁTICA DETECTABLE (posible campo cercano residual o "
                                    "reflexión de frontera, Cap. 4.6/8 -- no invalida alpha_app si el error "
                                    "vs. teoría es pequeño, pero repórtelo explícitamente en la tesis)")
        print(f"  R²={r_cuadrado:.4f} | RMSE={rmse:.4f} dB | DW={durbin_watson:.4f} "
              f"(rango sin autocorrelación [{DW_MIN},{DW_MAX}])")
        print(f"  Diagnóstico de residuos: {estructura_residual}")
        print(f"  Ajuste utilizable (R²>0.85 y RMSE<0.5): {validez}")
        print("----------------------------------\n")

        # -----------------------------------------------------------------
        # 5b. BARRIDO DE SENSIBILIDAD DE limite_inf (Cap. 4.6: el criterio
        # de Fraunhofer clásico asume medio SIN pérdidas). Reajusta M0 con
        # ventanas cada vez más alejadas de la antena, sobre los mismos
        # datos -- sin volver a correr MEEP.
        # -----------------------------------------------------------------
        print("  --- Barrido de sensibilidad de limite_inf (M0) ---")
        multiplicadores_prueba = sorted(set([1.5, 2.0, 2.5, 3.0, limite_inf / lambda_medio]))
        for mult in multiplicadores_prueba:
            li = mult * lambda_medio
            m2 = (r_coords > li) & (r_coords < limite_sup) & (intensidad_db > UMBRAL_RUIDO_DB)
            if np.sum(m2) > 20:
                r2, db2 = r_coords[m2], intensidad_db[m2]
                sl2, ic2 = np.polyfit(r2, db2, 1)
                ajuste = ajustar_modelo(modelo_M0, r2, db2, p0=[ic2, max(abs(sl2), 1e-6)],
                                         bounds=BOUNDS_M0, k_params=2)
                if ajuste is not None:
                    resultados_sensibilidad.append((mult, li, ajuste["popt"][1]))
                    print(f"    limite_inf={mult:.2f}*lambda ({li:.1f} mm): alpha_app={ajuste['popt'][1]:.4f} dB/mm")
        if len(resultados_sensibilidad) >= 2:
            resultados_sensibilidad.sort()
            alfa_vals = [x[2] for x in resultados_sensibilidad]
            if abs(alfa_vals[0]) > 1e-9:
                deriva_pct = 100 * (alfa_vals[-1] - alfa_vals[0]) / alfa_vals[0]
                print(f"  Deriva de alpha_app entre la ventana más angosta y la más ancha probada: "
                      f"{deriva_pct:.1f}% -- si es grande (>10-15%), confirma contaminación de campo "
                      f"cercano/reflexión aún presente en la ventana usada por defecto.\n")

        # -----------------------------------------------------------------
        # 5c. INCERTIDUMBRE DE alpha_app: CI POR pcov (asume residuos i.i.d.
        # gaussianos) vs. CI POR BOOTSTRAP DE BLOQUES MÓVILES (válido aun
        # con la autocorrelación que ya detectó Durbin-Watson). Ambos se
        # reportan siempre -- comparar su ancho es en sí mismo diagnóstico:
        # si el bootstrap es mucho más ancho que el de pcov, confirma que
        # ignorar la autocorrelación *subestimaría* la incertidumbre real.
        # -----------------------------------------------------------------
        pcov_ganador = validos[nombre_modelo]["pcov"]
        bounds_por_modelo = {"M0": BOUNDS_M0, "M1": BOUNDS_M1, "M2": BOUNDS_M2}[nombre_modelo]
        se_alfa = np.sqrt(pcov_ganador[1, 1]) if np.all(np.isfinite(pcov_ganador)) else np.nan

        print("  --- Incertidumbre de alpha_app ---")
        if np.isfinite(se_alfa):
            gl = len(r_seguro) - len(popt)
            t_crit = scipy_stats.t.ppf(0.975, df=gl)
            ci_naive = (alfa_real - t_crit * se_alfa, alfa_real + t_crit * se_alfa)
            print(f"    CI 95% (pcov, asume residuos i.i.d.):        "
                  f"[{ci_naive[0]:.4f}, {ci_naive[1]:.4f}] dB/mm  (ancho={ci_naive[1]-ci_naive[0]:.4f})")
        else:
            ci_naive = (np.nan, np.nan)
            print("    CI 95% (pcov): no disponible (covarianza no finita, revisar convergencia del ajuste)")

        alphas_boot, ci_boot, block_len_usado = bootstrap_bloques_moviles(
            r_seguro, residuos, {"M0": modelo_M0, "M1": modelo_M1, "M2": modelo_M2}[nombre_modelo],
            popt, bounds_por_modelo, n_boot=1500)
        if np.isfinite(ci_boot[0]):
            print(f"    CI 95% (bootstrap por bloques, block_len={block_len_usado}): "
                  f"[{ci_boot[0]:.4f}, {ci_boot[1]:.4f}] dB/mm  (ancho={ci_boot[1]-ci_boot[0]:.4f})")
            if np.isfinite(se_alfa) and (ci_naive[1] - ci_naive[0]) > 0:
                razon = (ci_boot[1] - ci_boot[0]) / (ci_naive[1] - ci_naive[0])
                print(f"    Bootstrap es {razon:.1f}x más ancho que pcov -- "
                      f"{'consistente con autocorrelación real en los residuos.' if razon > 1.3 else 'diferencia leve, los residuos se comportan casi i.i.d. en esta ventana.'}")
        else:
            print("    CI bootstrap: no se obtuvieron suficientes réplicas convergentes.")

        if alpha_teorico_dB_mm > 1e-9 and np.isfinite(ci_boot[0]):
            dentro_naive = ci_naive[0] <= alpha_teorico_dB_mm <= ci_naive[1] if np.isfinite(se_alfa) else None
            dentro_boot = ci_boot[0] <= alpha_teorico_dB_mm <= ci_boot[1]
            print(f"    alpha_teorico ({alpha_teorico_dB_mm:.4f}) respecto al CI bootstrap: "
                  f"{'DENTRO -- diferencia compatible con incertidumbre estadística' if dentro_boot else 'FUERA -- diferencia probablemente sistemática (campo cercano/reflexión, no ruido), ver Cap. 4.6/8'}")
        print("-----------------------------------\n")

else:
    idx = np.where((intensidad_db < UMBRAL_RUIDO_DB) & (r_coords > 2.0))[0]
    distancia_corte = r_coords[idx[0]] if len(idx) > 0 else R_max
    eq_texto, nombre_modelo, validez = f"Corte a {distancia_corte:.1f} mm", "Límite Operativo", "UMBRAL ALCANZADO"
    r_cuadrado = rmse = durbin_watson = alfa_real = 0
    estructura_residual = "N/A"
    r_seguro = linea_predicha = residuos = []
    ci_naive = ci_boot = (np.nan, np.nan)
    block_len_usado = None

# =====================================================================
# 6. EXPORTACIÓN A CSV CON METADATOS
# =====================================================================
carpeta_salida = "Resultados_Tesis_Fase2"
os.makedirs(carpeta_salida, exist_ok=True)
csv_filename = os.path.join(carpeta_salida, f"Resultados_Fase2_{nombre_medio}.csv")

with open(csv_filename, 'w', encoding='utf-8') as f:
    f.write(f"# SIMULACIÓN FDTD FASE 2: {nombre_medio.upper()}\n")
    f.write(f"# tan_delta={tan_delta_actual:.4f} | alpha_teorico={alpha_teorico_dB_mm:.4f} dB/mm | "
            f"lambda_medio={lambda_medio:.3f} mm | resolution={resolution} px/mm "
            f"(~{px_diametro_monopolo:.0f} px/diametro monopolo)\n")
    f.write(f"# Modelo Evaluado: {nombre_modelo} | Frontera: {tipo_frontera}\n")
    if distancia_corte is None:
        f.write(f"# Parametros: {eq_texto} | Ajuste utilizable (R2/RMSE): {validez}\n")
        f.write(f"# R^2: {r_cuadrado:.4f} | RMSE: {rmse:.4f} dB | DW: {durbin_watson:.4f} "
                f"(rango sin autocorrelacion [{DW_MIN},{DW_MAX}])\n")
        f.write(f"# Diagnostico de residuos: {estructura_residual}\n")
        if np.isfinite(ci_boot[0]):
            f.write(f"# CI 95% pcov: [{ci_naive[0]:.4f},{ci_naive[1]:.4f}] dB/mm | "
                    f"CI 95% bootstrap (block_len={block_len_usado}): [{ci_boot[0]:.4f},{ci_boot[1]:.4f}] dB/mm\n")
        if resultados_sensibilidad:
            f.write("# Sensibilidad limite_inf (mult_lambda, mm, alpha_app dB/mm): " +
                     "; ".join(f"({m:.2f},{li:.1f},{a:.4f})" for m, li, a in resultados_sensibilidad) + "\n")
    else:
        f.write(f"# SISTEMA COLAPSADO. Límite de Cobertura Absoluta: {distancia_corte:.2f} mm\n")
    f.write("#" + "=" * 60 + "\n")
    pd.DataFrame({'Radio_mm': r_coords, 'S_avg_Lineal': np.abs(intensidad_poynting),
                  'P_dB_Compensada': intensidad_db}).to_csv(f, index=False)

print(f"[ÉXITO] Datos crudos: {os.path.abspath(csv_filename)}")

# =====================================================================
# 7. GRAFICACIÓN
# =====================================================================
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8.5), gridspec_kw={'height_ratios': [3, 1]})
ax1.plot(r_coords, intensidad_db, color='firebrick', linewidth=2, label="Perfil Radial FDTD")

if distancia_corte is None and len(r_seguro) > 0:
    ax1.plot(r_seguro, linea_predicha, color='blue', linestyle='--', linewidth=2.5,
              label=f"Modelo {eq_texto} - {validez}")
elif distancia_corte is not None:
    ax1.axvline(x=distancia_corte, color='darkred', linestyle='--', linewidth=2,
                label=f"Colapso a {distancia_corte:.1f} mm")
    ax1.axvspan(distancia_corte, R_max, color='red', alpha=0.1)

ax1.axvspan(0, limite_inf, color='gray', alpha=0.12, label="Campo Cercano")
ax1.axvspan(limite_sup, R_max, color='black', alpha=0.06, label="Borde Absorbedor")
ax1.set_title(f"Propagación a 3 GHz: {nombre_medio.replace('_', ' ').title()} (tan$\\delta$={tan_delta_actual:.3f})",
              fontsize=13, fontweight='bold')
ax1.set_ylabel("Flujo Compensado por r² (dB)", fontsize=11)
ax1.set_ylim(np.max(intensidad_db[r_coords < limite_sup]) - 70, np.max(intensidad_db[r_coords < limite_sup]) + 10)
ax1.legend(loc="upper right", fontsize=9)
ax1.grid(True, ls="--", alpha=0.5)

if distancia_corte is None and len(r_seguro) > 0:
    ax2.scatter(r_seguro, residuos, color='purple', alpha=0.6, s=15)
    ax2.axhline(0, color='black', linewidth=1.5, linestyle='--')
    ax2.set_xlabel("Distancia Radial (mm)", fontsize=11)
    ax2.set_ylabel("Residuos (dB)", fontsize=10)
    caja_est = f"$R^2$: {r_cuadrado:.3f}\nRMSE: {rmse:.2f} dB\nDW: {durbin_watson:.2f}  [{DW_MIN},{DW_MAX}]"
    caja_est += "\n" + ("Sin estructura" if "sin estructura" in estructura_residual else "Estructura detectable*")
    if np.isfinite(ci_boot[0]):
        caja_est += f"\n$\\alpha_{{app}}$ CI95% boot: [{ci_boot[0]:.3f},{ci_boot[1]:.3f}]"
    ax2.text(0.02, 0.85, caja_est, transform=ax2.transAxes, fontsize=9, verticalalignment='top',
              bbox=dict(boxstyle="round", fc="white", alpha=0.9))
    ax2.grid(True, ls="--", alpha=0.4)
    if "sin estructura" not in estructura_residual:
        fig.text(0.5, 0.005, "*Ver Cap. 4.6/8: posible campo cercano residual o reflexión de frontera, "
                              "de magnitud pequeña (no invalida alpha_app si el error vs. teoría es bajo).",
                  ha='center', fontsize=8, style='italic', color='dimgray')

plt.tight_layout()
img_filename = os.path.join(carpeta_salida, f"Tesis_Resultado_{nombre_medio}.png")
plt.savefig(img_filename, dpi=300, bbox_inches='tight')
print(f"-> Gráfica guardada: {os.path.abspath(img_filename)}")
plt.show()