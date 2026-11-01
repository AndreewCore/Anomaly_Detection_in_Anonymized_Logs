"""anonlogs: efectos de la anonimización en la detección de fuerza bruta SSH.

Etapas del pipeline (un módulo por etapa): parsing → anonymization → features →
labeling/splitting → detection → evaluation → reporting. Los scripts de
``scripts/`` orquestan estas etapas; los notebooks solo importan desde aquí.
"""

__version__ = "0.1.0"
