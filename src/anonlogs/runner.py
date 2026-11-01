"""Ejecución de un run y escritura de sus artefactos en ``results/runs/<run_id>/``."""

from pathlib import Path

from anonlogs.matrix import RunSpec


def provenance() -> dict:
    """Devuelve hash del commit, si hay cambios sin commitear, y versiones de Python y librerías."""
    raise NotImplementedError


def is_complete(run_dir: Path) -> bool:
    """Un run está completo si existe ``metrics.json``: es lo último que se escribe."""
    return (run_dir / "metrics.json").is_file()


def execute_run(spec: RunSpec, experiment: dict, runs_dir: Path) -> Path:
    """Ejecuta un run completo y escribe sus artefactos.

    Orden: ``config.yaml`` (spec + semilla + procedencia) → ``run.log`` →
    ``scores.csv`` (unit_id, score, pred, label) → ``metrics.json``.
    ``metrics.json`` se escribe en un temporal y se renombra (atómico), así un
    run interrumpido nunca parece completo.

    Returns:
        Carpeta del run.
    """
    raise NotImplementedError
