"""
Experimento A/B para APU.
Corre uno o más despachadores sobre la misma configuración y semilla,
e imprime una tabla comparativa con los KPIs de cada uno.

Uso:
  PYTHONPATH=src python -m experiments.run_ab --version v0
  PYTHONPATH=src python -m experiments.run_ab --version v0 --config mina_andina
  PYTHONPATH=src python -m experiments.run_ab --version v0 --duracion 6
"""

import argparse
import os
import sys

# Añadir src/ al path cuando se ejecuta directamente (sin PYTHONPATH)
_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
if _src not in sys.path:
    sys.path.insert(0, _src)

from apu.sim.engine import MotorSimulacion, cargar_config
from apu.dispatch.baselines import ShortestQueue, Random, Nearest, SPTF, FixedGroup
from apu.metrics.kpis import calcular_kpis, imprimir_resumen


def _construir_fixed_group(config: dict) -> FixedGroup:
    """Asigna camiones a palas en ciclo (1→pala_1, 2→pala_2, ...)."""
    palas_ids = [p['id'] for p in config['palas']]
    camiones_ids = [c['id'] for c in config['camiones']]
    asignaciones = {
        c_id: palas_ids[i % len(palas_ids)]
        for i, c_id in enumerate(camiones_ids)
    }
    return FixedGroup(asignaciones)


def correr_v0(config: dict, duracion: float, seed: int):
    """
    v0: un solo despachador (ShortestQueue), salida por consola.
    Criterio de aceptación: corre 12 h simuladas en < 10 s reales.
    """
    dispatcher = ShortestQueue()
    engine = MotorSimulacion(config, dispatcher)
    t_elapsed = engine.correr(duracion)
    kpis = calcular_kpis(engine, t_elapsed)
    imprimir_resumen(kpis, config_nombre=config.get('nombre', ''))

    assert t_elapsed < 10.0, (
        f"La simulación tardó {t_elapsed:.1f} s (límite: 10 s). "
        "Algo está muy mal en el motor SimPy."
    )
    print(f"\n  ✓ Criterio v0 cumplido: {t_elapsed:.3f} s < 10 s")


def main():
    parser = argparse.ArgumentParser(
        description='APU — Motor de despacho camión-pala para minería a tajo abierto'
    )
    parser.add_argument(
        '--version', choices=['v0', 'v1', 'v2', 'v3'], default='v0',
        help='Versión del experimento a ejecutar'
    )
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument(
        '--config', default='mina_base',
        help='Nombre del archivo YAML en config/ (sin extensión)'
    )
    parser.add_argument(
        '--duracion', type=float, default=None,
        help='Duración en horas simuladas (sobreescribe el YAML)'
    )
    args = parser.parse_args()

    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..', 'config', f'{args.config}.yaml'
    )

    if not os.path.exists(config_path):
        print(f"Error: no se encontró el archivo de configuración '{config_path}'")
        sys.exit(1)

    config = cargar_config(config_path)
    duracion = args.duracion or config['simulacion']['duracion_horas']

    print(f"\n  Iniciando APU — versión {args.version}")
    print(f"  Config: {args.config}.yaml  |  Duración: {duracion} h  |  Semilla: {args.seed}")

    if args.version == 'v0':
        correr_v0(config, duracion, args.seed)
    else:
        print(f"\n  La versión '{args.version}' aún no está implementada.")
        print("  Confirma v0 y di 'adelante con v1' para continuar.")
        sys.exit(1)


if __name__ == '__main__':
    main()
