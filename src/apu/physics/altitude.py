"""
Derateo de potencia de motor por altitud.

Aspirado natural  → pérdida ≈ 3% cada 300 m sobre 1 500 msnm
Turboalimentado   → pérdida ≈ 2% cada 300 m sobre 2 500 msnm

Fuente: metodología de cálculo de rimpull publicada por fabricantes
(Caterpillar Performance Handbook, edición 47, sección Fleet Selection).
Los coeficientes exactos son del dominio YAML para facilitar calibración.
"""


def factor_derateo(altitud_msnm: float, config: dict) -> float:
    """
    Retorna el factor de potencia disponible ∈ (0, 1].

    A nivel del mar retorna 1.0 (sin pérdida).
    A mayor altitud, menos oxígeno → menos potencia efectiva → camiones más lentos.

    Parámetros del YAML (todos con valores por defecto razonables):
        tipo_aspiracion   : 'aspirado' | 'turboalimentado'
        coef_derateo      : fracción de pérdida por 300 m (p. ej. 0.03 = 3%)
        altitud_referencia: msnm a partir del cual empieza el derateo
    """
    tipo    = config.get('tipo_aspiracion', 'turboalimentado')
    coef    = config.get('coef_derateo', 0.02 if tipo == 'turboalimentado' else 0.03)
    alt_ref = config.get('altitud_referencia_msnm',
                          2500 if tipo == 'turboalimentado' else 1500)

    perdida = coef * max(0.0, altitud_msnm - alt_ref) / 300.0
    return max(0.10, 1.0 - perdida)
