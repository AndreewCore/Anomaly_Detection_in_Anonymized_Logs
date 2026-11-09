"""Etapa 4: expande la matriz y ejecuta cada run en results/runs/<run_id>/, saltando los completos.

Cada ejecución deja un registro en ``results/sessions/<...>/`` con un resumen
(nombre con fecha, usuario, nº de runs y filas, y duración).

Uso:
    python scripts/04_run_matrix.py --matrix configs/matrix_smoke.yaml --dry-run
    python scripts/04_run_matrix.py --matrix configs/matrix_smoke.yaml
"""

import argparse
import getpass
import json
import time
from datetime import datetime, timezone

import pandas as pd

from anonlogs.config import REPO_ROOT, load_yaml
from anonlogs.matrix import expand_matrix
from anonlogs.runner import execute_run, is_complete


def main() -> None:
    """Expande la matriz y ejecuta (o solo cuenta) los runs pendientes."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default="configs/experiment.yaml")
    parser.add_argument("--matrix", required=True)
    parser.add_argument("--dry-run", action="store_true", help="solo cuenta runs totales, hechos y pendientes")
    args = parser.parse_args()

    experiment = load_yaml(args.config)
    matrix = load_yaml(args.matrix)
    runs = expand_matrix(matrix)
    runs_dir = REPO_ROOT / experiment["paths"]["runs"]
    pending = [r for r in runs if not is_complete(runs_dir / r.run_id)]
    print(f"runs totales: {len(runs)} | completos: {len(runs) - len(pending)} | pendientes: {len(pending)}")
    if args.dry_run:
        return

    phase = matrix.get("phase", "sin_fase")
    user = getpass.getuser()
    start = datetime.now(timezone.utc)
    stamp = start.strftime("%Y-%m-%d_%H%M")
    sessions_dir = REPO_ROOT / "results" / "sessions"
    session_dir = sessions_dir / f"{stamp}__{phase}__{user}__en_curso"
    session_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    resumen, n_filas = [], 0
    for i, spec in enumerate(pending, 1):
        labeling_cfg = matrix.get("labeling", {"any": {"rule": "any"}})[spec.labeling]
        try:
            execute_run(spec, experiment, runs_dir, labeling_cfg)
            metrics = json.loads((runs_dir / spec.run_id / "metrics.json").read_text())
            n_filas += int(metrics.get("n_test", 0) or 0)
            resumen.append({"run_id": spec.run_id, "dataset": spec.dataset,
                            "tratamiento": spec.tratamiento, "campo": spec.campo,
                            "unit": spec.unit, "labeling": spec.labeling,
                            "detector": spec.detector, "seed": spec.seed,
                            "status": metrics.get("status", "ok"),
                            "f1": metrics.get("f1"), "recall": metrics.get("recall")})
        except Exception as e:  # un run no debe tumbar toda la corrida
            resumen.append({"run_id": spec.run_id, "status": f"error: {e}"})
            print(f"  [{i}/{len(pending)}] ERROR en {spec.run_id}: {e}")
        if i % 50 == 0 or i == len(pending):
            print(f"  {i}/{len(pending)} runs")

    dur_min = round((time.time() - t0) / 60, 1)
    df = pd.DataFrame(resumen)
    df.to_csv(session_dir / "runs.csv", index=False)
    (session_dir / "manifest.json").write_text(json.dumps({
        "phase": phase, "user": user, "matrix": args.matrix,
        "started_utc": start.isoformat(), "n_runs": len(pending),
        "n_filas_evaluadas": n_filas, "duracion_min": dur_min,
        "errores": int(df["status"].astype(str).str.startswith("error").sum()) if not df.empty else 0,
    }, indent=2), encoding="utf-8")

    # Renombra la sesión con el resumen (igual que las capturas del laboratorio).
    final = sessions_dir / f"{stamp}__{phase}__{user}__{len(pending)}runs-{n_filas}filas__{dur_min}min"
    session_dir.rename(final)
    print(f"sesión: {final}")


if __name__ == "__main__":
    main()
