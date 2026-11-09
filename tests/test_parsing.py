"""Pruebas del parseo: dos formatos de log, línea de tiempo virtual y enlace del GT."""

import pandas as pd

from anonlogs import parsing

# Formato del laboratorio (RFC 3339) y de Loghub (tradicional sin año).
LAB = (
    "2026-11-09T14:00:01.100000+00:00 victim sshd[1001]: Failed password for admin from 172.28.1.101 port 5001 ssh2\n"
    "2026-11-09T14:00:02.200000+00:00 victim sshd[1002]: Accepted password for alice from 172.28.10.11 port 5002 ssh2\n"
    "2026-11-09T14:00:03.300000+00:00 victim sshd[1003]: Invalid user bob from 172.28.1.101 port 5003\n"
)
LOGHUB = "Dec 10 06:55:46 LabSZ sshd[24200]: Failed password for root from 183.62.140.253 port 61379 ssh2\n"


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_parsea_formato_lab(tmp_path):
    """Extrae tipo de evento, usuario, IP y pid del formato RFC 3339."""
    ev = parsing.parse_auth_log(_write(tmp_path, "a.log", LAB), "lab_x", segment=1)
    assert list(ev["event_type"]) == ["failed_password", "accepted", "invalid_user"]
    assert ev.iloc[0]["user"] == "admin" and ev.iloc[0]["src_ip"] == "172.28.1.101"
    assert ev.iloc[0]["pid"] == 1001
    assert ev.iloc[0]["event_id"] == "lab_x:seg1:0"


def test_parsea_formato_loghub(tmp_path):
    """El formato tradicional (sin año) también se parsea, asumiendo el año dado."""
    ev = parsing.parse_auth_log(_write(tmp_path, "h.log", LOGHUB), "loghub", year=2023)
    assert ev.iloc[0]["event_type"] == "failed_password"
    assert ev.iloc[0]["src_ip"] == "183.62.140.253"
    assert ev.iloc[0]["timestamp"].year == 2023


def test_linea_de_tiempo_virtual(tmp_path):
    """El segmento 2 arranca después del 1 en la línea virtual, sin solaparse."""
    f1 = parsing.parse_auth_log(_write(tmp_path, "s1.log", LAB), "lab_x", segment=1)
    # Segmento 2: mismas marcas reales, pero debe quedar después en la virtual.
    f2 = parsing.parse_auth_log(_write(tmp_path, "s2.log", LAB), "lab_x", segment=2)
    merged = parsing.build_virtual_timeline([f2, f1])  # desordenado a propósito
    seg1 = merged[merged["segment"] == 1]["timestamp"].max()
    seg2 = merged[merged["segment"] == 2]["timestamp"].min()
    assert seg2 > seg1
    assert merged["timestamp"].is_monotonic_increasing


def test_enlace_gt_propaga_por_conexion(tmp_path):
    """El GT marca la conexión atacante completa (mismo pid), no solo la línea con IP."""
    ev = parsing.parse_auth_log(_write(tmp_path, "a.log", LAB), "lab_x", segment=1)
    ev = parsing.build_virtual_timeline([ev])
    gt = pd.DataFrame({
        "scenario": ["x"], "segment": [1], "burst_id": [0], "attacker": ["a1"],
        "src_ip": ["172.28.1.101"], "user": ["admin"],
        "ts_start": ["2026-11-09T14:00:01.000000+00:00"],
        "ts_end": ["2026-11-09T14:00:01.500000+00:00"],
    })
    gt["ts_start"] = pd.to_datetime(gt["ts_start"], utc=True)
    gt["ts_end"] = pd.to_datetime(gt["ts_end"], utc=True)
    labels = parsing.link_ground_truth(ev, gt)
    by_id = labels.set_index("event_id")["is_attack"]
    # La línea del intento (pid 1001) es ataque; el login legítimo de alice no.
    assert by_id["lab_x:seg1:0"] == 1
    assert by_id["lab_x:seg1:1"] == 0


def test_revisiones_sobrescriben(tmp_path):
    """Una revisión humana cambia la etiqueta y marca la fuente."""
    labels = pd.DataFrame({"event_id": ["e1", "e2"], "is_attack": [0, 0], "fuente": ["auto", "auto"]})
    rev = pd.DataFrame({"event_id": ["e2"], "is_attack": [1]})
    out = parsing.apply_revisions(labels, rev).set_index("event_id")
    assert out.loc["e2", "is_attack"] == 1 and out.loc["e2", "fuente"] == "revision"
    assert out.loc["e1", "fuente"] == "auto"
