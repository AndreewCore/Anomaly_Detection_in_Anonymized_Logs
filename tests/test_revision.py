"""Pruebas de las revisiones automáticas del Ground Truth (3 estrategias)."""

import numpy as np
import pandas as pd

from anonlogs import revision


def _dudosos(n_atk=6, n_leg=4):
    """Dudosos sintéticos: ``n_atk`` desde IP atacante (verdad=1) y ``n_leg`` legítimos (verdad=0)."""
    ips = ["172.28.1.101"] * n_atk + ["172.28.10.11"] * n_leg
    return pd.DataFrame({
        "event_id": [f"e{i}" for i in range(n_atk + n_leg)],
        "src_ip": ips,
        "motivo": [""] * (n_atk + n_leg),
    })


def test_lab_truth_por_ip():
    """La verdad del lab sale de la IP: atacante → 1, legítima → 0."""
    dud = _dudosos()
    truth = revision.lab_truth(dud, {"172.28.1.101"})
    assert truth.tolist() == [1, 1, 1, 1, 1, 1, 0, 0, 0, 0]


def test_cobertura_revisa_fraccion_con_verdad():
    """cobertura: revisa round(frac·n) dudosos y siempre con la etiqueta verdadera."""
    dud = _dudosos()
    truth = revision.lab_truth(dud, {"172.28.1.101"})
    rev = revision.simulate_revisiones(dud, truth, "cobertura", frac=0.6, seed=1)
    assert len(rev) == 6  # round(0.6 * 10)
    verdad = dict(zip(dud["event_id"], truth))
    assert all(rev.set_index("event_id")["is_attack"][e] == verdad[e] for e in rev["event_id"])


def test_aleatorio_cubre_todos_e_ignora_verdad():
    """aleatorio: una fila por dudoso, etiqueta 0/1 (no necesariamente la verdad)."""
    dud = _dudosos()
    truth = revision.lab_truth(dud, {"172.28.1.101"})
    rev = revision.simulate_revisiones(dud, truth, "aleatorio", seed=1)
    assert len(rev) == len(dud)
    assert set(rev["is_attack"].unique()) <= {0, 1}


def test_aciertos_converge_a_rate():
    """aciertos: con muchos dudosos, la tasa de acierto tiende a ``rate``."""
    dud = _dudosos(1000, 1000)
    truth = revision.lab_truth(dud, {"172.28.1.101"})
    rev = revision.simulate_revisiones(dud, truth, "aciertos", rate=0.75, seed=1)
    hit = (rev["is_attack"].to_numpy() == truth.to_numpy()).mean()
    assert abs(hit - 0.75) < 0.05


def test_reproducible_por_semilla():
    """Misma semilla → mismo CSV de revisiones, en los tres modos."""
    dud = _dudosos()
    truth = revision.lab_truth(dud, {"172.28.1.101"})
    for mode in revision.MODES:
        a = revision.simulate_revisiones(dud, truth, mode, seed=7)
        b = revision.simulate_revisiones(dud, truth, mode, seed=7)
        assert a.equals(b)


def test_modo_invalido():
    """Un modo fuera de MODES es un error explícito."""
    dud = _dudosos()
    truth = revision.lab_truth(dud, {"172.28.1.101"})
    try:
        revision.simulate_revisiones(dud, truth, "inexistente")
        assert False, "debió lanzar ValueError"
    except ValueError:
        pass
