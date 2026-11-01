"""Etapa 4: expande la matriz y ejecuta cada run en results/runs/<run_id>/, saltando los completos.

Uso:
    python scripts/04_run_matrix.py --matrix configs/matrix_smoke.yaml --dry-run
    python scripts/04_run_matrix.py --matrix configs/matrix_exploracion.yaml
"""

import argparse

from anonlogs.config import REPO_ROOT, load_yaml
from anonlogs.matrix import expand_matrix
from anonlogs.runner import is_complete


def main() -> None:
    """Lee los argumentos, expande la matriz y ejecuta (o solo cuenta) los runs pendientes."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default="configs/experiment.yaml")
    parser.add_argument("--matrix", required=True)
    parser.add_argument("--dry-run", action="store_true", help="solo cuenta runs totales, hechos y pendientes")
    args = parser.parse_args()

    experiment = load_yaml(args.config)
    runs = expand_matrix(load_yaml(args.matrix))
    runs_dir = REPO_ROOT / experiment["paths"]["runs"]
    pending = [r for r in runs if not is_complete(runs_dir / r.run_id)]
    print(f"runs totales: {len(runs)} | completos: {len(runs) - len(pending)} | pendientes: {len(pending)}")
    if args.dry_run:
        return
    raise NotImplementedError("runner.execute_run aún no está implementado")


if __name__ == "__main__":
    main()
