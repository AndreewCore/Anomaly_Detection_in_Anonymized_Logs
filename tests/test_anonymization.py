"""Pruebas de los tres tratamientos de anonimización y de la exposición residual."""

import pandas as pd

from anonlogs.anonymization import apply_treatment, pseudonymize, generalize_ip
from anonlogs.evaluation.exposure import residual_exposure

PARAMS = {"suppression_token": "<SUPRIMIDO>", "ipv4_prefix": 24, "hmac_digest_chars": 16}


def _events() -> pd.DataFrame:
    """Dos eventos con usuarios que se contienen (admin/administrator) y una IP."""
    return pd.DataFrame({
        "event_id": ["e0", "e1"],
        "timestamp_real": ["t0", "t1"], "host": ["victim", "victim"],
        "process": ["sshd", "sshd"], "pid": [1, 2],
        "event_type": ["failed_password", "failed_password"],
        "user": ["admin", "administrator"],
        "src_ip": ["172.28.1.101", "172.28.1.101"],
        "message": ["Failed password for admin from 172.28.1.101 port 5001 ssh2",
                    "Failed password for administrator from 172.28.1.101 port 5002 ssh2"],
    })


def test_generalize_ip_a_24():
    """Una IPv4 se reduce a su red /24; lo que no es IPv4 queda igual."""
    assert generalize_ip("172.28.1.101", 24) == "172.28.1.0/24"
    assert generalize_ip("no-es-ip", 24) == "no-es-ip"


def test_pseudonimo_consistente_y_depende_de_la_sal():
    """Mismo valor → mismo seudónimo; otra sal → otro seudónimo."""
    a = pseudonymize("admin", b"sal1", 16, "u_")
    assert a == pseudonymize("admin", b"sal1", 16, "u_")
    assert a != pseudonymize("admin", b"sal2", 16, "u_")
    assert a.startswith("u_") and len(a) == 18


def test_supresion_colapsa_entidades():
    """Supresión de IP: todas las IPs quedan con el mismo token, en columna y texto."""
    out = apply_treatment(_events(), "suprimida", "ip", PARAMS)
    assert set(out["src_ip"]) == {"<SUPRIMIDO>"}
    assert "172.28.1.101" not in " ".join(out["message"])


def test_admin_no_rompe_administrator():
    """Al tratar el usuario, 'admin' no debe corromper 'administrator' en el texto."""
    out = apply_treatment(_events(), "seudonimizada", "usuario", PARAMS, salt=b"sal")
    # administrator sigue siendo una sola entidad distinta de admin.
    msg1 = out.iloc[1]["message"]
    assert "administrator" not in msg1  # fue reemplazado como un token completo
    seud_admin = out.iloc[0]["user"]
    seud_administrator = out.iloc[1]["user"]
    assert seud_admin != seud_administrator
    # El seudónimo de administrator aparece entero en su mensaje (no partido).
    assert seud_administrator in msg1


def test_exposicion_cero_en_suprimida_ambos():
    """suprimida/ambos no deja ningún usuario ni IP original literal: 0 %."""
    ev = _events()
    out = apply_treatment(ev, "suprimida", "ambos", PARAMS)
    exp = residual_exposure(ev, out)
    assert exp["exposure_users_pct"] == 0.0
    assert exp["exposure_ips_pct"] == 0.0


def test_exposicion_alta_en_original():
    """Sin tratamiento, todos los identificadores siguen presentes: 100 %."""
    ev = _events()
    exp = residual_exposure(ev, ev)
    assert exp["exposure_users_pct"] == 100.0
    assert exp["exposure_ips_pct"] == 100.0


def test_generalizacion_mantiene_red_en_texto():
    """ip_generalizada deja la red /24 visible en el texto libre."""
    out = apply_treatment(_events(), "ip_generalizada", "ip", PARAMS)
    assert "172.28.1.0/24" in out.iloc[0]["message"]
