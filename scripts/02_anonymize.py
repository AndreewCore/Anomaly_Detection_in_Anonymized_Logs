"""Etapa 2: genera data/processed/<dataset>/<tratamiento>/<campo>/ para cada par de la matriz.

Uso:
    python scripts/02_anonymize.py --matrix configs/matrix_exploracion.yaml
"""

import argparse


def main() -> None:
    """Lee los argumentos y ejecuta la etapa."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default="configs/experiment.yaml")
    parser.add_argument("--matrix", required=True)
    parser.parse_args()
    raise NotImplementedError


if __name__ == "__main__":
    main()
