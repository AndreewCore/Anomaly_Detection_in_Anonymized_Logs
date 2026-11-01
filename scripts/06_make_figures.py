"""Etapa 6: genera results/figures/ (PDF + PNG) a partir de results/tables/ y results/runs/.

Uso:
    python scripts/06_make_figures.py --phase confirmacion
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
