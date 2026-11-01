"""Etapa 5: reconstruye results/tables/ (consolidado, agregados, Wilcoxon+Holm) solo desde results/runs/.

Uso:
    python scripts/05_build_tables.py --phase confirmacion
"""

import argparse


def main() -> None:
    """Lee los argumentos y ejecuta la etapa."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default="configs/experiment.yaml")
    parser.add_argument("--phase", choices=["smoke", "exploracion", "confirmacion"], required=True)
    parser.parse_args()
    raise NotImplementedError


if __name__ == "__main__":
    main()
