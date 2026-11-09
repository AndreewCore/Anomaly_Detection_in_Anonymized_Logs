"""Etapa 2: genera data/processed/<dataset>/<tratamiento>/<campo>/ para cada par de la matriz.

Por cada (dataset, tratamiento, campo) escribe la tabla anonimizada, un ``auth.log``
anonimizado legible y ``exposure.json`` con la exposición residual frente al original.

Uso:
    python scripts/02_anonymize.py --matrix configs/matrix_smoke.yaml
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from anonlogs.config import REPO_ROOT, load_yaml, get_salt
from anonlogs.anonymization import apply_treatment
from anonlogs.evaluation.exposure import residual_exposure


def _reconstruir_log(events: pd.DataFrame) -> str:
    """Rearma un auth.log legible desde la tabla (para inspeccionar la anonimización)."""
    lineas = []
    for r in events.itertuples(index=False):
        pid = f"[{int(r.pid)}]" if pd.notna(r.pid) else ""
        lineas.append(f"{r.timestamp_real} {r.host} {r.process}{pid}: {r.message}")
    return "\n".join(lineas) + "\n"


def main() -> None:
    """Aplica todos los pares (tratamiento, campo) de la matriz a cada dataset."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default="configs/experiment.yaml")
    parser.add_argument("--matrix", required=True)
    args = parser.parse_args()

    exp = load_yaml(args.config)
    matrix = load_yaml(args.matrix)
    anon_params = exp["anonymization"]
    pairs = [(t["tratamiento"], t["campo"]) for t in matrix["treatments"]]

    # La sal solo se carga si algún par la necesita, para no exigir .env sin motivo.
    salt = get_salt() if any(t == "seudonimizada" for t, _ in pairs) else None

    for dataset in matrix["datasets"]:
        interim = REPO_ROOT / exp["paths"]["interim"] / dataset / "events.csv"
        if not interim.is_file():
            print(f"{dataset}: falta {interim} (corre la etapa 1). Se omite.")
            continue
        events = pd.read_csv(interim)

        for trat, campo in pairs:
            anon = apply_treatment(events, trat, campo, anon_params, salt)
            out_dir = REPO_ROOT / exp["paths"]["processed"] / dataset / trat / campo
            out_dir.mkdir(parents=True, exist_ok=True)
            anon.to_csv(out_dir / "events.csv", index=False)
            (out_dir / "auth.log").write_text(_reconstruir_log(anon), encoding="utf-8")
            exp_res = residual_exposure(events, anon)
            (out_dir / "exposure.json").write_text(json.dumps(exp_res, indent=2), encoding="utf-8")
            print(f"{dataset}/{trat}/{campo}: usuarios={exp_res['exposure_users_pct']}% "
                  f"ips={exp_res['exposure_ips_pct']}%")


if __name__ == "__main__":
    main()
