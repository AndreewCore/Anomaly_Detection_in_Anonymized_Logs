"""Revisiones automáticas del Ground Truth: sustituyen la marca humana a mano.

La revisión de los dudosos (``parsing.find_dudosos``) la hacía una persona marcando
cada caso en ``<dataset>_revisiones.csv``, así que el resultado dependía de quién la
hiciera. Aquí se simula con tres estrategias reproducibles, para medir el *efecto* de
la calidad de la revisión sobre la detección sin arrastrar la variabilidad de cada
revisor (y sin editar CSV a mano).

La "verdad del lab" de cada dudoso se conoce sin ambigüedad: las IPs atacantes solo
atacan y las legítimas solo generan tráfico normal, así que un evento desde una IP
atacante es ataque (1) y desde una IP legítima es normal (0). Las bitácoras legit
solo corroboran los typos; no cambian la etiqueta.
"""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from anonlogs import parsing

# Estrategias de revisión. Agregar una = una rama en ``simulate_revisiones`` + su nombre aquí.
MODES = ("cobertura", "aleatorio", "aciertos")

_REV_COLUMNS = ["event_id", "is_attack", "motivo", "revisor", "fecha"]


def lab_truth(dudosos: pd.DataFrame, attacker_ips: set[str]) -> pd.Series:
    """Etiqueta verdadera (0/1) de cada dudoso según el laboratorio.

    En el lab la IP de origen basta: atacante → ataque (1), legítima → normal (0).
    Alineada con el índice de ``dudosos``.
    """
    ips = set(attacker_ips)
    return dudosos["src_ip"].map(lambda ip: 1 if ip in ips else 0).astype(int)


def simulate_revisiones(dudosos: pd.DataFrame, truth: pd.Series, mode: str, *,
                        frac: float = 0.60, rate: float = 0.75, seed: int = 0) -> pd.DataFrame:
    """Simula un revisor sobre los dudosos y devuelve el CSV de revisiones.

    Args:
        dudosos: salida de ``parsing.find_dudosos`` (``event_id``, ``src_ip``, ``motivo``…).
        truth: etiqueta verdadera por dudoso (ver :func:`lab_truth`), mismo orden.
        mode:
            ``cobertura`` — revisa con la etiqueta verdadera una fracción ``frac`` de
            los dudosos (subconjunto elegido con semilla); el resto no lleva fila y
            conserva la etiqueta automática. Revisión parcial pero fiel.
            ``aleatorio`` — revisa todos, pero asigna la etiqueta al azar 50/50 con
            semilla, sin mirar la verdad. Baseline de "revisor que adivina".
            ``aciertos`` — revisa todos, acertando la etiqueta verdadera con
            probabilidad ``rate`` (el resto se invierte). Revisión completa pero
            imperfecta.
        frac: fracción revisada en ``cobertura`` (0–1).
        rate: tasa de acierto en ``aciertos`` (0–1).
        seed: semilla; dos corridas con la misma semilla dan el mismo CSV.

    Returns:
        DataFrame ``event_id, is_attack, motivo, revisor, fecha`` para
        ``parsing.apply_revisions``. En ``cobertura`` solo trae las filas revisadas.
    """
    if mode not in MODES:
        raise ValueError(f"Modo de revisión desconocido: {mode!r} (usa {MODES})")

    rng = np.random.default_rng(seed)
    d = dudosos.reset_index(drop=True)
    truth = pd.Series(list(truth), dtype=int)
    n = len(d)
    hoy = datetime.now(timezone.utc).date().isoformat()

    if mode == "cobertura":
        # Subconjunto reproducible: permutar con semilla y tomar los primeros k.
        k = round(frac * n)
        sel = sorted(rng.permutation(n)[:k].tolist())
        d = d.iloc[sel].reset_index(drop=True)
        is_attack = truth.iloc[sel].to_numpy()
    elif mode == "aleatorio":
        is_attack = rng.integers(0, 2, size=n)
    else:  # aciertos
        acierta = rng.random(n) < rate
        is_attack = np.where(acierta, truth.to_numpy(), 1 - truth.to_numpy())

    return pd.DataFrame({
        "event_id": d["event_id"].to_numpy(),
        "is_attack": np.asarray(is_attack).astype(int),
        "motivo": d["motivo"].to_numpy() if "motivo" in d else "",
        "revisor": f"auto:{mode}",
        "fecha": hoy,
    }, columns=_REV_COLUMNS)


def build_revisiones(events: pd.DataFrame, ground_truth: pd.DataFrame, mode: str, *,
                     frac: float = 0.60, rate: float = 0.75, seed: int = 0,
                     legit: pd.DataFrame | None = None) -> pd.DataFrame:
    """Calcula los dudosos y su verdad, y simula la revisión en un solo paso.

    Punto de entrada común del script y del flag de ``01_parse_logs.py``. ``legit`` es
    opcional y solo corrobora (la verdad se deriva de las IPs del GT).
    """
    labels = parsing.link_ground_truth(events, ground_truth)
    dudosos = parsing.find_dudosos(events, labels, ground_truth)
    attacker_ips = set(ground_truth["src_ip"]) if not ground_truth.empty else set()
    truth = lab_truth(dudosos, attacker_ips)
    return simulate_revisiones(dudosos, truth, mode, frac=frac, rate=rate, seed=seed)


def load_legit(gt_dir: str | Path, dataset: str) -> pd.DataFrame | None:
    """Carga la bitácora legítima consolidada (``<dataset>_legit.csv``) si se ingestó.

    Devuelve ``None`` cuando no existe: la verdad por IP no la necesita, solo sirve
    de auditoría para los typos.
    """
    p = Path(gt_dir) / f"{dataset}_legit.csv"
    return pd.read_csv(p) if p.is_file() else None
