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
    args = ("d1", "original", "ninguno", "ip", ("fallos_por_ip",), "ventana", "any", 60, "umbral", None)
    assert RunSpec(*args).run_id == RunSpec(*args).run_id
    assert RunSpec(*args).run_id.startswith("d1__")


def test_run_id_depende_de_unidad_y_etiquetado():
    """Cambiar la unidad o la regla de etiquetado produce un run_id distinto (D1/D2)."""
    base = ("d1", "original", "ninguno", "ip", ("fallos_por_ip",), "ventana", "any", 60, "umbral", None)
    otra_unidad = RunSpec(*base[:5], "ventana_ip", *base[6:])
    otra_regla = RunSpec(*base[:6], "frac50", *base[7:])
    assert RunSpec(*base).run_id != otra_unidad.run_id != otra_regla.run_id


def test_expande_ejes_d1_d2():
    """units y labeling multiplican los runs; umbral_calibrado corre sin semilla."""
    m = {**BASE, "units": ["ventana", "ventana_ip"],
         "labeling": {"any": {"rule": "any"}, "frac50": {"rule": "fraction", "min_fraction": 0.5}},
         "detectors": ["isolation_forest", "umbral_calibrado"]}
    runs = expand_matrix(m)
    # 2 pares × 2 unidades × 2 etiquetados = 8 combinaciones base.
    assert sum(r.detector == "umbral_calibrado" for r in runs) == 8          # sin semilla
    assert sum(r.detector == "isolation_forest" for r in runs) == 8 * 3      # × 3 semillas


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
