"""Prueba de humo: el paquete y sus subpaquetes se importan sin errores."""

import importlib

import pytest

MODULES = [
    "anonlogs", "anonlogs.config", "anonlogs.matrix", "anonlogs.parsing",
    "anonlogs.anonymization", "anonlogs.features", "anonlogs.labeling",
    "anonlogs.splitting", "anonlogs.runner", "anonlogs.detection",
    "anonlogs.evaluation.metrics", "anonlogs.evaluation.exposure",
    "anonlogs.reporting.aggregate", "anonlogs.reporting.stats", "anonlogs.reporting.figures",
]


@pytest.mark.parametrize("name", MODULES)
def test_import(name):
    """Cada módulo se importa; detecta errores de sintaxis o dependencias faltantes."""
    importlib.import_module(name)


def test_registry_has_all_detectors():
    """Los tres detectores de la matriz están registrados."""
    from anonlogs.detection import REGISTRY
    assert set(REGISTRY) == {"isolation_forest", "ssif", "umbral"}
