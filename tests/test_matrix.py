"""Pruebas de la expansión de la matriz y del run_id."""

import pytest

from anonlogs.config import load_yaml
from anonlogs.matrix import RunSpec, expand_matrix

BASE = {
    "datasets": ["d1"],
    "treatments": [{"tratamiento": "original", "campo": "ninguno"},
                   {"tratamiento": "seudonimizada", "campo": "ip"}],
    "rule_sets": {"ip": ["fallos_por_ip"]},
    "window_seconds": [60],
    "detectors": ["isolation_forest", "umbral"],
    "seeds": [0, 1, 2],
}


def test_run_id_is_stable():
    """El mismo spec produce siempre el mismo run_id (base de la reanudación)."""
    spec = RunSpec("d1", "original", "ninguno", "ip", ("fallos_por_ip",), 60, "umbral", None)
    again = RunSpec("d1", "original", "ninguno", "ip", ("fallos_por_ip",), 60, "umbral", None)
    assert spec.run_id == again.run_id
    assert spec.run_id.startswith("d1__")


def test_run_id_ignores_yaml_key_order():
    """Reordenar las claves del YAML no cambia los run_id."""
    reordered = dict(reversed(list(BASE.items())))
    assert [r.run_id for r in expand_matrix(BASE)] == [r.run_id for r in expand_matrix(reordered)]


def test_seedless_detector_runs_once():
    """umbral no tiene semilla: 1 run por combinación; isolation_forest: 1 por semilla."""
    runs = expand_matrix(BASE)
    assert sum(r.detector == "umbral" for r in runs) == 2          # 2 pares × 1
    assert sum(r.detector == "isolation_forest" for r in runs) == 6  # 2 pares × 3 semillas


def test_invalid_treatment_pair_rejected():
    """ip_generalizada + usuario no es una combinación válida (decisión D3)."""
    bad = {**BASE, "treatments": [{"tratamiento": "ip_generalizada", "campo": "usuario"}]}
    with pytest.raises(ValueError):
        expand_matrix(bad)


@pytest.mark.parametrize("name", ["matrix_smoke", "matrix_exploracion", "matrix_confirmacion"])
def test_repo_matrices_expand(name):
    """Las matrices del repo son válidas."""
    assert expand_matrix(load_yaml(f"configs/{name}.yaml"))
