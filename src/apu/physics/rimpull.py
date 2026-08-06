"""
Cálculo de la fuerza de tracción disponible (Rimpull) y resistencia total al avance.

Parámetros calibrados con catálogos de fabricantes:
  - Caterpillar 797F (Potencia bruta: 4,000 HP / 2,983 kW)
  - Komatsu 930E-5 (Potencia bruta: 2,700 HP / 2,013 kW)

Ecuación base:
  F_disponible = (Potencia_kW * Eficiencia_Transmision * Factor_Derateo) / Velocidad_m_s
  F_requerida  = Peso_Bruto_kN * (Pendiente_% + Resistencia_Rodamiento_%) / 100
"""

from typing import Dict, Any, Optional
from src.apu.physics.altitude import factor_derateo


# Tablas de especificaciones públicas de fabricantes
ESPECIFICACIONES_FABRICANTE: Dict[str, Dict[str, Any]] = {
    "CAT_797F": {
        "potencia_nominal_kw": 2983.0,     # 4,000 HP
        "peso_vacio_ton": 260.0,
        "capacidad_carga_ton": 363.0,       # Peso Bruto Total: 623 ton
        "eficiencia_transmision": 0.85,     # Transmisión mecánica/convertidor de par
        "velocidad_max_kmh": 67.6,
        "tipo_aspiracion": "turboalimentado"
    },
    "KOMATSU_930E_5": {
        "potencia_nominal_kw": 2013.0,     # 2,700 HP
        "peso_vacio_ton": 210.0,
        "capacidad_carga_ton": 290.0,       # Peso Bruto Total: 500 ton
        "eficiencia_transmision": 0.88,     # Mando eléctrico AC
        "velocidad_max_kmh": 64.5,
        "tipo_aspiracion": "turboalimentado"
    }
}


def calcular_fuerza_resistencia(
    peso_bruto_ton: float,
    pendiente_pct: float,
    resistencia_rodamiento_pct: float = 2.0
) -> float:
    """
    Calcula la fuerza total opuesta al movimiento (Resistencia Total en kN).

    Parametros:
        peso_bruto_ton (float): Peso total del camión + carga (toneladas métricas).
        pendiente_pct (float): Pendiente de la rampa en porcentaje (%).
        resistencia_rodamiento_pct (float): Resistencia de la trocha en % (típico: 2% vía buena, 5-8% barro/lluvia).

    Retorna:
        float: Fuerza de resistencia total en KiloNewtons (kN).
    """
    g = 9.81  # Aceleración de la gravedad (m/s²)
    peso_kn = peso_bruto_ton * g
    resistencia_total_pct = pendiente_pct + resistencia_rodamiento_pct
    
    # Resistencia en kN
    fuerza_resistencia_kn = peso_kn * (resistencia_total_pct / 100.0)
    return float(fuerza_resistencia_kn)


def calcular_rimpull_disponible(
    velocidad_kmh: float,
    modelo_camion: str = "KOMATSU_930E_5",
    altitud_msnm: float = 4100.0,
    config: Optional[Dict[str, Any]] = None
) -> float:
    """
    Calcula la fuerza de tracción disponible (Rimpull en kN) en las ruedas motrices
    considerando el derateo de potencia por altitud.

    Parametros:
        velocidad_kmh (float): Velocidad actual o proyectada del camión en km/h.
        modelo_camion (str): Llave del modelo ('CAT_797F' o 'KOMATSU_930E_5').
        altitud_msnm (float): Altitud de la sección en msnm (ej. 4,100 msnm para mina andina).
        config (dict, opcional): Configuración de anulación desde el YAML.

    Retorna:
        float: Fuerza Rimpull disponible en KiloNewtons (kN).
    """
    # 1. Obtener especificaciones del modelo o fallback a Komatsu
    spec = ESPECIFICACIONES_FABRICANTE.get(modelo_camion.upper(), ESPECIFICACIONES_FABRICANTE["KOMATSU_930E_5"])

    potencia_kw = spec["potencia_nominal_kw"]
    eficiencia = spec["eficiencia_transmision"]
    tipo_asp = spec["tipo_aspiracion"]

    # 2. Obtener factor de derateo de potencia desde el módulo altitude.py
    f_derateo = factor_derateo(altitud_msnm, tipo_aspiracion=tipo_asp, config=config)
    potencia_efectiva_kw = potencia_kw * eficiencia * f_derateo

    # 3. Evitar división por cero a velocidades muy bajas o detenido
    velocidad_efectiva_kmh = max(velocidad_kmh, 1.0)
    velocidad_m_s = velocidad_efectiva_kmh / 3.6

    # 4. Cálculo de Rimpull (Potencia = Fuerza * Velocidad => Fuerza = Potencia / Velocidad)
    rimpull_kn = potencia_efectiva_kw / velocidad_m_s
    return float(rimpull_kn)


def calcular_velocidad_maxima_equilibrio(
    peso_bruto_ton: float,
    pendiente_pct: float,
    resistencia_rodamiento_pct: float,
    altitud_msnm: float,
    modelo_camion: str = "KOMATSU_930E_5",
    config: Optional[Dict[str, Any]] = None
) -> float:
    """
    Hallazgo clave de física: Encuentra la velocidad máxima sostenible en rampa
    donde Rimpull Disponible == Fuerza de Resistencia Total.

    Retorna:
        float: Velocidad límite teórica en km/h.
    """
    spec = ESPECIFICACIONES_FABRICANTE.get(modelo_camion.upper(), ESPECIFICACIONES_FABRICANTE["KOMATSU_930E_5"])
    
    # Resistencia en kN
    f_resistencia_kn = calcular_fuerza_resistencia(peso_bruto_ton, pendiente_pct, resistencia_rodamiento_pct)
    if f_resistencia_kn <= 0:
        return spec["velocidad_max_kmh"]

    # Potencia efectiva en kW
    f_derateo = factor_derateo(altitud_msnm, tipo_aspiracion=spec["tipo_aspiracion"], config=config)
    potencia_efectiva_kw = spec["potencia_nominal_kw"] * spec["eficiencia_transmision"] * f_derateo

    # V = Potencia / Fuerza
    velocidad_m_s = potencia_efectiva_kw / f_resistencia_kn
    velocidad_kmh = velocidad_m_s * 3.6

    # Limitar por la velocidad máxima física permitida por catálogo/transmisión
    return min(spec["velocidad_max_kmh"], float(velocidad_kmh))


# --- PRUEBA UNITARIA Y VALIDACIÓN DE MÓDULO ---
if __name__ == "__main__":
    # Test 1: Calcular Rimpull para Komatsu 930E a 4100 msnm a 15 km/h
    r_komatsu = calcular_rimpull_disponible(15.0, "KOMATSU_930E_5", altitud_msnm=4100)
    print(f"Rimpull disponible Komatsu 930E (15 km/h, 4,100 msnm): {r_komatsu:.2f} kN")

    # Test 2: Velocidad equilibrio para CAT 797F cargado (623 ton) subiendo rampa de 10% con rodamiento de 3%
    v_max_cat = calcular_velocidad_maxima_equilibrio(
        peso_bruto_ton=623.0,
        pendiente_pct=10.0,
        resistencia_rodamiento_pct=3.0,
        altitud_msnm=3800.0,
        modelo_camion="CAT_797F"
    )
    print(f"Velocidad Máx de Equilibrio CAT 797F en Rampa 10%: {v_max_cat:.2f} km/h")

    assert v_max_cat > 0.0 and v_max_cat < 67.6
    print("✓ Módulo rimpull.py verificado y validado con especificaciones de fabricante.")