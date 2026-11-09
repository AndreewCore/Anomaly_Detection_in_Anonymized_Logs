"""Pruebas de las features según la unidad de análisis (D1)."""

import pandas as pd

from anonlogs.features import RULES, build_features


def _events() -> pd.DataFrame:
    """Una ventana: la IP A falla 3 veces contra 2 usuarios; la IP B, 1 vez."""
    base = pd.Timestamp("2026-11-09T14:00:00Z")
    filas = [
        ("e0", 0, "A", "admin", "failed_password"),
        ("e1", 1, "A", "admin", "failed_password"),
        ("e2", 2, "A", "root", "failed_password"),
        ("e3", 3, "B", "admin", "failed_password"),
        ("e4", 4, "C", "alice", "accepted"),
    ]
    return pd.DataFrame([{
        "event_id": eid, "timestamp": base + pd.Timedelta(seconds=s),
        "src_ip": ip, "user": u, "event_type": et,
    } for eid, s, ip, u, et in filas])


def test_unidad_ventana_usa_maximos():
    """unit=ventana: una fila; fallos_por_ip = máx sobre IPs (A con 3)."""
    f = build_features(_events(), list(RULES), window_seconds=300, unit="ventana")
    assert len(f) == 1
    assert f.iloc[0]["fallos_por_ip"] == 3           # IP A
    assert f.iloc[0]["usuarios_unicos_por_ip"] == 2  # A tocó admin y root
    assert f.iloc[0]["fallos_por_ventana"] == 4      # 4 fallos (accepted no cuenta)


def test_unidad_ventana_ip():
    """unit=ventana_ip: una fila por IP con fallos; la IP A tiene 3 y 2 usuarios."""
    f = build_features(_events(), list(RULES), window_seconds=300, unit="ventana_ip")
    fa = f[f["unit_id"].str.contains("ip=A")].iloc[0]
    assert fa["fallos_por_ip"] == 3
    assert fa["usuarios_unicos_por_ip"] == 2
    # Hay una fila para A y otra para B (C solo tiene un accepted).
    assert set(f["unit_id"].str.split("ip=").str[1]) == {"A", "B", "C"}


def test_unidad_ventana_usuario():
    """unit=ventana_usuario: fila por usuario; admin fue atacado por A y B."""
    f = build_features(_events(), list(RULES), window_seconds=300, unit="ventana_usuario")
    adm = f[f["unit_id"].str.contains("user=admin")].iloc[0]
    assert adm["fallos_por_usuario"] == 3            # 3 fallos contra admin (e0,e1 de A; e3 de B)
    assert adm["fallos_por_ip"] == 3                 # máx entre A(3) y B(1)


def test_event_ids_se_conservan():
    """Cada unidad guarda sus event_id, que el etiquetado necesita."""
    f = build_features(_events(), list(RULES), window_seconds=300, unit="ventana")
    assert set(f.iloc[0]["event_ids"].split(";")) == {"e0", "e1", "e2", "e3", "e4"}
