"""
Derateo de potencia del motor por altitud sobre el nivel del mar.

Dos modos configurables en el YAML (motor.tipo_aspiracion):
  - 'aspirado':       ~3% de pérdida por cada 300 m sobre 1,500 msnm
  - 'turboalimentado': pérdida menor, empieza a notarse sobre ~3,000 msnm

El coeficiente exacto debe validarse contra las curvas de potencia del
fabricante específico del equipo (CAT, Komatsu, Liebherr, etc.).

Se implementa en v2.
"""

from typing import Dict, Any, Optional


def factor_derateo(
    altitud_msnm: float, 
    tipo_aspiracion: str = 'turboalimentado', 
    config: Optional[Dict[str, Any]] = None
) -> float:
    """
    Calcula el factor de derateo de potencia del motor diésel debido a la menor
    densidad del aire a gran altitud sobre el nivel del mar (msnm).

    Parametros:
        altitud_msnm (float): Altitud del tramo u operación en metros sobre el nivel del mar.
        tipo_aspiracion (str): 'aspirado' o 'turboalimentado' (por defecto 'turboalimentado').
        config (dict, opcional): Diccionario de configuración de motor/mina del YAML para 
                                 personalizar umbrales y tasas por fabricante (CAT/Komatsu).

    Retorna:
        float: Coeficiente multiplicador de potencia nominal en el rango [0.0, 1.0].
               1.0 representa 100% de potencia nominal (sin derateo).
    """
    # 1. Asegurar que altitudes negativas o a nivel del mar no derateen la potencia
    if altitud_msnm <= 0:
        return 1.0

    # 2. Cargar parámetros desde el YAML o usar valores estándar por defecto
    cfg_motor = config.get('motor', {}) if config else {}
    
    # Lectura de parámetros según tipo de aspiración (permite sobreescritura desde el YAML)
    if tipo_aspiracion.lower() == 'aspirado':
        altitud_base = cfg_motor.get('altitud_base_aspirado', 1500.0)      # msnm donde inicia la pérdida
        tasa_perdida = cfg_motor.get('tasa_perdida_aspirado', 0.03)         # 3% de pérdida
        intervalo_m = cfg_motor.get('intervalo_metros_aspirado', 300.0)     # por cada 300 m
    
    elif tipo_aspiracion.lower() in ['turboalimentado', 'turbo']:
        altitud_base = cfg_motor.get('altitud_base_turbo', 3000.0)         # msnm donde inicia la pérdida
        tasa_perdida = cfg_motor.get('tasa_perdida_turbo', 0.015)          # 1.5% de pérdida (menor por turbocompresor)
        intervalo_m = cfg_motor.get('intervalo_metros_turbo', 300.0)       # por cada 300 m
    
    else:
        # Fallback por seguridad si el tipo no coincide
        altitud_base = 3000.0
        tasa_perdida = 0.015
        intervalo_m = 300.0

    # 3. Si la altitud no supera el umbral base, se entrega el 100% de potencia
    if altitud_msnm <= altitud_base:
        return 1.0

    # 4. Cálculo de la altitud excedente y pérdida acumulada
    altitud_excedente = altitud_msnm - altitud_base
    porcentaje_perdida = (altitud_excedente / intervalo_m) * tasa_perdida

    # 5. Aplicar derateo y limitar el valor en el rango [0.1, 1.0] por límites físicos del motor
    factor = 1.0 - porcentaje_perdida
    return max(0.1, min(1.0, float(factor)))


# --- PRUEBA UNITARIA RÁPIDA DE VERIFICACIÓN ---
if __name__ == "__main__":
    # Test 1: Nivel del mar
    assert factor_derateo(0) == 1.0
    
    # Test 2: Aspirado a 3,000 msnm (1,500m de exceso -> (1500/300)*3% = 15% pérdida -> factor 0.85)
    f_asp = factor_derateo(3000, tipo_aspiracion='aspirado')
    print(f"Factor Derateo Aspirado (3,000 msnm): {f_asp:.3f}")
    assert round(f_asp, 2) == 0.85

    # Test 3: Turboalimentado a 4,100 msnm (Mina Andina typical: 1,100m exceso -> (1100/300)*1.5% = ~5.5% pérdida -> factor 0.945)
    f_turbo = factor_derateo(4100, tipo_aspiracion='turboalimentado')
    print(f"Factor Derateo Turbo (4,100 msnm - Mina Andina): {f_turbo:.3f}")
    assert f_turbo < 1.0

    print("✓ Módulo altitude.py verificado correctamente.")