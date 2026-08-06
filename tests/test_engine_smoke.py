from pathlib import Path

import yaml

from src.apu.dispatch.baselines import ShortestQueue
from src.apu.sim.engine import MotorSimulacion


def test_simulacion_basica_genera_resumen_valido():
    config_path = Path(__file__).resolve().parents[1] / "config" / "mina_base.yaml"
    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    motor = MotorSimulacion(config, ShortestQueue())
    tiempo_real = motor.correr(duracion_horas=0.5)
    resumen = motor.resumen()

    assert tiempo_real >= 0
    assert resumen["ciclos_totales"] > 0
    assert resumen["ton_total"] > 0
    assert resumen["n_eventos_log"] > 0
    assert resumen["promedio_espera_por_ciclo_min"] >= 0
